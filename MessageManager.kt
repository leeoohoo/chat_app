package com.immotors.aicoder.common

import com.google.gson.Gson
import com.immotors.aicoder.ai.client.v2.ChatCompletionRequest
import com.immotors.aicoder.ai.client.v2.ChatMessage
import com.immotors.aicoder.ai.client.v2.Function
import com.immotors.aicoder.ai.client.v2.HttpRequestHandler
import com.immotors.aicoder.ai.client.v2.StreamResponse
import com.immotors.aicoder.ai.client.v2.ToolCall
import com.intellij.openapi.diagnostic.Logger
import com.immotors.aicoder.service.ConversationService
import com.immotors.aicoder.service.FileUploadService
import com.intellij.workspaceModel.ide.impl.workspaceModelMetrics
import kotlinx.coroutines.DelicateCoroutinesApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.html.SUMMARY
import kotlinx.serialization.json.Json

/**
 * 消息管理器
 * 对应Python版本的MessageManager
 * 
 * @author lilei
 * @date 2025-01-XX
 */
class MessageManager(
    private val conversationContext: ConversationContext,
    private val conversationService: ConversationService = ConversationService(),
    private val fileUploadService: FileUploadService = FileUploadService()
) {
    
    private val logger = Logger.getInstance(MessageManager::class.java)
    private val gson = Gson()
    
    val conversationId = conversationContext.conversationId
    var userMessage = conversationContext.userMessage
        private set
    private val fileList = conversationContext.fileList
    private val globalContext = conversationContext.globalContext
    private val messagesHistory = mutableListOf<Map<String, Any>>()

    /**
     * 获取用于API调用的消息历史记录
     * 
     * 逻辑：
     * 1. 获取最近的maxMessages条消息
     * 2. 检查这些消息中是否包含原始用户需求
     * 3. 如果没有，将原始需求插入到结果列表的下标0位置
     * 4. 如果历史消息总数超过限制，在下标1位置添加占位符
     * 
     * @param maxMessages 要保留的最近消息数量，默认为10
     * @return 处理后的消息历史列表
     */
    fun getMessagesHistory(maxMessages: Int = 10): List<Map<String, Any>> {
        // 获取消息总数
        val totalMessages = messagesHistory.size
        
        // 如果消息总数小于等于最大限制，直接返回所有消息
        if (totalMessages <= maxMessages) {
            return messagesHistory.toList()
        }
        
        // 获取最近的maxMessages条消息
        val recentMessages = messagesHistory.takeLast(maxMessages).toMutableList()
        
        // 检查原始用户需求是否在最近消息中
        var originalRequestInRecent = false
        if (userMessage.isNotEmpty()) {
            for (msg in recentMessages) {
                if (msg["role"] == "user" && 
                    msg["content"] is String && 
                    msg["content"] == userMessage) {
                    originalRequestInRecent = true
                    break
                }
            }
        }
        
        // 创建结果列表，初始包含最近消息
        val result = recentMessages.toMutableList()
        
        // 如果原始需求不在最近消息中，将其插入到结果列表的下标0位置
        if (!originalRequestInRecent && userMessage.isNotEmpty()) {
            val originalRequest = mapOf<String, Any>(
                "role" to "user",
                "content" to userMessage
            )
            result.add(0, originalRequest)
        }
        
        // 如果历史消息总数超过最大限制，在下标1位置添加占位符
        if (totalMessages > maxMessages) {
            val placeholder = mapOf<String, Any>(
                "role" to "user",
                "content" to "... 部分历史对话已省略，仅展示最近内容 ..."
            )
            // 在原始需求之后添加占位符（下标1位置）
            result.add(1, placeholder)
        }
        
        return result
    }
    
    /**
     * 确保全局上下文（如果已设置）作为系统消息，始终位于
     * 发送给 AI 的消息列表的最前面
     * 
     * @param messages 由getMessagesHistory返回的消息列表
     * @return 处理后的消息列表，全局上下文（如果存在）在最前面
     */
    fun ensureGlobalContextInMessages(messages: List<Map<String, Any>>): List<Map<String, Any>> {
        if (globalContext.isNullOrEmpty()) {
            // 如果没有设置全局上下文，直接返回原始消息列表
            return messages
        }
        
        // 创建全局上下文对应的系统消息
        val systemContextMsg = mapOf<String, Any>(
            "role" to "system", 
            "content" to globalContext
        )
        
        // 检查messages列表是否为空，或者第一条消息是否已经是我们的全局上下文
        if (messages.isEmpty()) {
            println("ensureGlobalContextInMessages收到空消息列表，仅返回全局上下文")
            return listOf(systemContextMsg)
        }
        
        if (messages.first() == systemContextMsg) {
            println("全局上下文已是第一条消息，无需重复添加")
            return messages
        }
        
        // 需要将全局上下文添加到列表开头
        println("将全局上下文添加到消息列表开头")
        
        // 创建一个新列表，将全局上下文放在最前面，然后跟上原始messages列表的所有内容
        return listOf(systemContextMsg) + messages
    }
    
    /**
     * 清空消息历史
     */
    fun clearMessagesHistory(): MessageManager {
        messagesHistory.clear()
        return this
    }
    
    /**
     * 设置用户消息，包含图片描述处理
     */
    suspend fun setUserMessage(userMessage: String) {
        val imageDescriptions = mutableListOf<String>()
        
        if (!fileList.isNullOrEmpty()) {
            val files = fileUploadService.getFilesByIds(fileList)
            files?.forEach { file ->
                if (file["content_type"]?.toString()?.contains("image") == true) {
                    val fileName = file["file_name"]?.toString() ?: ""
                    val fileDescription = file["file_description"]?.toString() ?: ""
                    imageDescriptions.add("\n图片名称 $fileName: 图片描述$fileDescription\n")
                }
            }
        }
        
        this.userMessage = if (imageDescriptions.isNotEmpty()) {
            userMessage + imageDescriptions.joinToString("")
        } else {
            userMessage
        }
    }
    
    /**
     * 设置历史消息
     */
    fun setHistoryMessages(messages: List<Map<String, Any>>): MessageManager {
        messagesHistory.clear()
        messagesHistory.addAll(messages)
        return this
    }
    
    /**
     * 添加消息到历史记录
     */
    fun addMessage(message: Map<String, Any>): MessageManager {
        messagesHistory.add(message)
        return this
    }
    
    /**
     * 添加用户消息
     * 🔥 重构：本地保存的同时自动进行远程保存
     */
    fun addUserMessage(content: String): MessageManager {
        val message = mapOf("role" to "user", "content" to content)
        
        // 本地保存
        addMessage(message)
        
        // 异步远程保存
        if (conversationId.isNotEmpty()) {
            GlobalScope.launch(Dispatchers.IO) {
                try {
                    conversationService.addMessage(
                        conversationId = conversationId,
                        role = "user",
                        content = content
                    )
                    logger.info("✅ 用户消息已保存到远程服务器")
                } catch (e: Exception) {
                    logger.warn("⚠️ 保存用户消息到远程失败: ${e.message}")
                }
            }
        }
        
        return this
    }

    fun updateUserMessage(content: String) {
        this.userMessage = content
    }
    
    /**
     * 添加助手消息
     * 🔥 重构：本地保存的同时自动进行远程保存
     */
    fun addAssistantMessage(content: String, toolCalls: List<Map<String, Any>>? = null): MessageManager {
        println("保存助手回答的内容[$content, $toolCalls]")
        
        val message = mutableMapOf<String, Any>("role" to "assistant")
        
        if (content.isEmpty() && !toolCalls.isNullOrEmpty()) {
            message["content"] = "调用工具：${toolCalls.first()["name"]}"
        } else {
            message["content"] = content
        }
        
        if (!toolCalls.isNullOrEmpty()) {
            message["tool_calls"] = toolCalls
        }
        
        // 本地保存
        addMessage(message)
        
        // 异步远程保存
        if (conversationId.isNotEmpty()) {
            GlobalScope.launch(Dispatchers.IO) {
                try {
                    val streamResult = mapOf<String, Any?>(
                        "content" to content,
                        "tool_calls" to toolCalls
                    )
                    saveStreamResponse(streamResult)
                    logger.info("✅ 助手消息已保存到远程服务器")
                } catch (e: Exception) {
                    logger.warn("⚠️ 保存助手消息到远程失败: ${e.message}")
                }
            }
        }
        
        return this
    }
    
    /**
     * 添加工具消息
     * 🔥 重构：本地保存的同时自动进行远程保存
     * @param toolCallId 工具调用ID
     * @param content 工具结果内容
     * @param toolCall 工具调用信息（可选，用于同时保存工具调用）
     */
    fun addToolMessage(toolCallId: String, content: String, toolCall: Map<String, Any>? = null): MessageManager {
        // 从对话上下文中获取AI类型
        val aiType = conversationContext.aiType.lowercase()
        val modelName = conversationContext.modelName
        
        // 🔥 调试：记录原始content长度和内容片段
        println("[DEBUG] addToolMessage - 原始content长度: ${content.length}, 前100字符: ${content.take(100)}")

        val message = getMessage(modelName, content, toolCallId, aiType)

        println("添加工具消息，AI类型: $aiType, 角色: ${message["role"]}")
        
        // 本地保存
        addMessage(message)
        
        // 异步远程保存
        saveToolMessageToRemote(conversationId, toolCall, content)
        
        return this
    }





    suspend fun addToolMessage(toolCallId: String, content: String, toolCall: Map<String, Any>? = null, httpRequestHandler: HttpRequestHandler, callback: ((String, String) -> Unit)? = null): MessageManager {
        //1 判断 content 的长度
        // 如果长度超过1000 需要调用httpRequestHandler 中的
        callback?.invoke("text", " --- \n\n")
        callback?.invoke("text", "好,请容我三思！！")
        var executeResult:StreamResponse? = null;

        if (content.length > 1000) {
            executeResult = httpRequestHandler.sendStreamRequest(
                context=conversationContext,
                requestBody= this.createChatCompletionRequest(content),
                callback=callback
            )
        }

        callback?.invoke("text", " --- \n\n")
        val summary = executeResult?.content
        val result = summary ?: content
        val message = getMessage(conversationContext.modelName, result, toolCallId, conversationContext.aiType.lowercase())
        addMessage(message)
        saveToolMessageToRemote(conversationId, toolCall, result, summary)
        // 从对话上下文中获取AI类型
        return this
    }



    @OptIn(DelicateCoroutinesApi::class)
    private fun saveToolMessageToRemote(
        conversationId: String,
        toolCall: Map<String, Any>?, // 根据实际类型调整，比如 ToolCall?
        content: String,
        summary: String? = ""
    ) {
        if (conversationId.isNotEmpty()) {
            GlobalScope.launch(Dispatchers.IO) {
                try {
                    if (toolCall != null) {
                        // 同时保存工具调用和结果
                        saveToolCall(toolCall)
                        saveToolResult(content,summary)
                    } else {
                        // 只保存工具结果
                        saveToolResult(content,summary)
                    }
                } catch (e: Exception) {
                    logger.warn("⚠️ 保存工具消息到远程失败: ${e.message}")
                }
            }
        }
    }



    fun getMessage(modelName: String, content: String, toolCallId: String, aiType: String): Map<String, Any> {
        val message = when {
            // 千问模型使用 "tool" 角色
            aiType.contains("qwen") || aiType.contains("tongyi")  || modelName.contains("kimi") ->  {
                val msg = mapOf<String, Any>(
                    "role" to "tool",
                    "tool_call_id" to toolCallId,
                    "content" to content
                )
                // 🔥 调试：检查构造后的message中content是否完整
                val msgContent = msg["content"] as? String ?: ""
                println("[DEBUG] 千问模型 - message构造后content长度: ${msgContent.length}, 前100字符: ${msgContent.take(100)}")
                msg
            }

            // 其他模型（如Claude等）使用 "user" 角色，内容为复杂格式
            else -> {
                val msg = mapOf<String, Any>(
                    "role" to "user",
                    "content" to listOf(
                        mapOf(
                            "type" to "tool_result",
                            "tool_use_id" to toolCallId,
                            "content" to content
                        )
                    )
                )
                // 🔥 调试：检查构造后的message中嵌套content是否完整
                val msgContentList = msg["content"] as? List<*>
                val nestedContent = (msgContentList?.firstOrNull() as? Map<*, *>)?.get("content") as? String ?: ""
                println("[DEBUG] 其他模型 - message构造后嵌套content长度: ${nestedContent.length}, 前100字符: ${nestedContent.take(100)}")
                msg
            }
        }
        return message
    }

    fun getMessageProcessingSystemContent(): String {
        return "请帮我总结一下这个内容，对其内容进行精简，将主要信息提取出来"
    }

    fun createChatCompletionRequest(content: String): ChatCompletionRequest{
        val messages = mutableListOf<ChatMessage>()
        messages.add(
            ChatMessage(
                role = "system",
                content = getMessageProcessingSystemContent()
            )
        )
        messages.add(
            ChatMessage(
                role = "user",
                content = "请帮我对一下内容进行总结 \n\n [content: $content]"
            )
        )
        return ChatCompletionRequest(
            model = conversationContext.modelName,
            messages = messages,
            stream = true,
            temperature = 0.7,

        )

    }

    /**
     * 保存流式响应结果到会话记录
     */
    suspend fun saveStreamResponse(streamResult: Map<String, Any?>, role: String = "assistant"): Boolean {
        if (conversationId.isEmpty() || streamResult.isEmpty()) {
            return false
        }
        
        return try {
            // 提取内容
            val content = streamResult["content"]?.toString() ?: ""
            if (content.isEmpty()) {
                return false
            }
            
            // 提取元数据
            val metadata = mutableMapOf<String, Any>()
            
            // 处理工具调用
            streamResult["tool_calls"]?.let { toolCalls ->
                if (toolCalls is List<*> && toolCalls.isNotEmpty()) {
                    metadata["tool_calls"] = toolCalls
                }
            }
            
            // 保存消息
            conversationService.addMessage(
                conversationId = conversationId,
                role = role,
                content = content,
                metadata = metadata.ifEmpty { null }
            )
            
            delay(500) // 对应Python的time.sleep(0.5)
            true
            
        } catch (e: Exception) {
            println("保存流式响应失败: ${e.message}")
            false
        }
    }
    
    /**
     * 保存工具调用信息到会话记录
     */
    suspend fun saveToolCall(toolCall: Map<String, Any>): Boolean {
        if (conversationId.isEmpty()) {
            return false
        }
        
        return try {
            // 将工具调用转换为字符串
            val toolCallContent = gson.toJson(toolCall)
            
            // 保存工具调用
            conversationService.addMessage(
                conversationId = conversationId,
                role = "tool_call", // 使用"tool_call"角色标识工具调用
                content = toolCallContent
            )
            
            delay(500)
            true
            
        } catch (e: Exception) {
            println("保存工具调用失败: ${e.message}")
            false
        }
    }
    
    /**
     * 保存工具调用结果到会话记录
     */
    suspend fun saveToolResult(toolResult: String,summary: String? = ""): Boolean {
        if (conversationId.isEmpty()) {
            return false
        }


        return try {
            val metadata = mutableMapOf<String, Any>()
            if (!summary.isNullOrEmpty()) {
                metadata["summary"] = summary
            }
            // 直接保存工具调用结果字符串
            conversationService.addMessage(
                conversationId = conversationId,
                role = "tool_result", // 使用"tool_result"角色标识工具结果
                content = toolResult,
                metadata = metadata
            )
            
            delay(500)
            true
            
        } catch (e: Exception) {
            println("保存工具调用结果失败: ${e.message}")
            false
        }
    }

    /**
     * 🔥 新增：按顺序保存工具调用及其结果，确保原子性和正确性
     */
    suspend fun saveToolCallAndResult(toolCall: Map<String, Any>, toolResult: String): Boolean {
        if (conversationId.isEmpty()) {
            return false
        }

        return try {
            // 1. 首先，保存工具调用
            saveToolCall(toolCall)

            // 2. 然后，保存工具结果
            saveToolResult(toolResult)

            true
        } catch (e: Exception) {
            println("保存工具调用和结果序列失败: ${e.message}")
            false
        }
    }
    
    /**
     * 获取消息历史记录数量
     */
    fun getMessageCount(): Int = messagesHistory.size
    
    /**
     * 获取最后一条消息
     */
    fun getLastMessage(): Map<String, Any>? = messagesHistory.lastOrNull()
    
    /**
     * 获取指定角色的消息数量
     */
    fun getMessageCountByRole(role: String): Int {
        return messagesHistory.count { it["role"] == role }
    }
    
    /**
     * 更新消息历史（用于工具调用后的消息更新）
     */
    fun updateMessagesHistory(newMessages: List<Map<String, Any>>) {
        messagesHistory.clear()
        messagesHistory.addAll(newMessages)
        println("更新消息历史，消息数: ${newMessages.size}")
    }
    
    override fun toString(): String {
        return "MessageManager(conversationId=$conversationId, " +
                "messageCount=${getMessageCount()}, " +
                "userMessageCount=${getMessageCountByRole("user")}, " +
                "assistantMessageCount=${getMessageCountByRole("assistant")})"
    }

    fun addExpertMessage(toolName: String, toolResult: String) {

        if (conversationId.isNotEmpty()) {
            GlobalScope.launch(Dispatchers.IO) {
                try {
                    conversationService.addMessage(
                        conversationId = conversationId,
                        role = toolName,
                        content = toolResult
                    )
                    logger.info("✅ 用户消息已保存到远程服务器")
                } catch (e: Exception) {
                    logger.warn("⚠️ 保存用户消息到远程失败: ${e.message}")
                }
            }
        }
    }
}