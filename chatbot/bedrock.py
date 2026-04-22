"""
bedrock.py — Bedrock communication layer.

Handles all Amazon Nova Pro / Nova Lite calls:
  - Non-streaming (_call_nova)
  - SSE streaming (_stream_nova)
  - Message list builder (_build_messages)
  - Friendly error mapper (_friendly_error)
"""
import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)

_REGION = os.environ.get('CHATBOT_AWS_REGION', 'us-east-1')

MODEL_PRIMARY  = os.environ.get('CHATBOT_AGENT_MODEL_PRIMARY',  'amazon.nova-pro-v1:0')
MODEL_FALLBACK = os.environ.get('CHATBOT_AGENT_MODEL_FALLBACK', 'amazon.nova-lite-v1:0')

_bedrock = boto3.client('bedrock-runtime', region_name=_REGION)


def _build_nova_body(messages: list, system_prompt: str) -> dict:
    """Build request body for Amazon Nova models."""
    nova_messages = []
    for m in messages:
        content_val = m.get('content', '')
        if isinstance(content_val, str):
            content_val = [{'text': content_val}]
        nova_messages.append({'role': m['role'], 'content': content_val})
    return {
        'messages': nova_messages,
        'system': [{'text': system_prompt}],
        'inferenceConfig': {
            'maxTokens': 1024,
            'temperature': 0.7,
        },
    }


def call_nova(messages: list, system_prompt: str) -> str:
    """Non-streaming Nova call. Tries primary model then fallback."""
    body = json.dumps(_build_nova_body(messages, system_prompt))
    for model_id in (MODEL_PRIMARY, MODEL_FALLBACK):
        try:
            response = _bedrock.invoke_model(
                modelId=model_id,
                body=body,
                contentType='application/json',
                accept='application/json',
            )
            result = json.loads(response['body'].read())
            return result['output']['message']['content'][0]['text']
        except Exception as e:
            logger.warning("bedrock: model %s failed: %s" % (model_id, str(e)))
    raise RuntimeError("All Bedrock models failed.")


def stream_nova(messages: list, system_prompt: str):
    """Generator that yields text chunks from Nova via SSE streaming."""
    body = json.dumps(_build_nova_body(messages, system_prompt))
    last_error = None
    for model_id in (MODEL_PRIMARY, MODEL_FALLBACK):
        try:
            response = _bedrock.invoke_model_with_response_stream(
                modelId=model_id,
                body=body,
                contentType='application/json',
                accept='application/json',
            )
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'])
                if 'contentBlockDelta' in chunk:
                    text = chunk['contentBlockDelta'].get('delta', {}).get('text', '')
                    if text:
                        yield text
            return  # success
        except Exception as e:
            last_error = e
            logger.warning("bedrock: stream model %s failed: %s" % (model_id, str(e)))
    raise RuntimeError("All Bedrock streaming models failed. Last error: " + str(last_error))


def build_messages(history: list, user_message: str) -> list:
    """Convert conversation history into a clean Nova message list."""
    messages = []
    for h in history:
        role = h.get('role', '')
        content = str(h.get('content', '')).strip()
        if role in ('user', 'assistant') and content:
            messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': user_message})
    # Ensure starts with 'user'
    while messages and messages[0]['role'] != 'user':
        messages.pop(0)
    return messages


def friendly_error(raw: str) -> str:
    """Map exception strings to user-friendly error messages."""
    raw_lower = raw.lower()
    if 'budget' in raw_lower or 'limit' in raw_lower:
        return ('⚠️ It looks like you may have reached your budget limit. '
                'Please check your budget on the dashboard before launching.')
    if 'throttl' in raw_lower or 'rate' in raw_lower:
        return '⚠️ Too many requests right now. Please wait a moment and try again.'
    if 'quota' in raw_lower or 'servicequota' in raw_lower:
        return ('⚠️ AWS service quota reached for this instance type. '
                'Try a smaller instance or contact your admin.')
    if 'access' in raw_lower or 'permission' in raw_lower or 'unauthorized' in raw_lower:
        return '⚠️ Permission denied. Please contact your platform administrator.'
    if 'model' in raw_lower or 'bedrock' in raw_lower:
        return ('⚠️ The AI model is temporarily unavailable. '
                'Please use the step-by-step wizard on the main page instead.')
    return ('⚠️ Something went wrong. Please try again, or use the step-by-step '
            'launch wizard on the main page.')
