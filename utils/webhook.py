import discord
from exceptions.client_exceptions import WebhookETCError, WebhookNoPermissionError

async def send_msg_as_pretend_user(channel: discord.TextChannel, user: discord.Member, 
                                   content: str | None = None, 
                                   file: discord.File | None = None,
                                   embed: discord.Embed | None = None):
    """
    Emoji를 사용한 유저의 메세지를 큰 이미지로 내보내는 용도로 사용하는 함수

    Args:
        channel (discord.TextChannel): 메세지를 보낼 채널
        user (discord.Member): 메세지를 보낸 유저
        content (str | None, optional): 메세지 내용. Defaults to None.
        file (discord.File | None, optional): 첨부할 파일. Defaults to None.
        embed (discord.Embed | None, optional): 첨부할 임베드. Defaults to None.
    """
    try:
        # 1. channel webhook 가져오기
        webhooks = await channel.webhooks()

        # 2. 봇 전용 webhook 확인
        webhook_name = "Bot_Proxy_Webhook"
        webhook = discord.utils.get(webhooks, name=webhook_name)

        # 3. 없으면 새로 생성
        if not webhook:
            webhook = await channel.create_webhook(name=webhook_name)

        if file is not None:
            # 4. webhook으로 메세지 보내기
            await webhook.send(
                content=content,
                username=user.display_name,
                avatar_url=user.display_avatar.url if user.display_avatar else None,
                file=file,
                embed=embed
            )
        else:
            await webhook.send(
                content=content,
                username=user.display_name,
                avatar_url=user.display_avatar.url if user.display_avatar else None,
                embed=embed
            )
            
    # permission error 발생시 예외 처리 (403 Forbidden)
    except discord.Forbidden as e:
        raise WebhookNoPermissionError(
            f"[webhook] No Permission. 채널: {channel.name} (ID: {channel.id})"
        ) from e
    
    except discord.HTTPException as e:
        raise WebhookETCError(
            f"[webhook] HTTP Error. 채널: {channel.name} (ID: {channel.id}). "
            f"에러: {e}"
        ) from e