import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
    ChatContext,
    ChatMessage
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import function_tool, RunContext
from livekit.plugins import sarvam
from mem0 import AsyncMemoryClient

logger = logging.getLogger("agent")

load_dotenv()

RAG_USER_ID = "user-anuj-1"
mem0_client = AsyncMemoryClient()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""
            <role> You are an AI customer service agent for SwiftCart who helps customers with their inquiries, issues and requests. You represent the company and aim to provide excellent, friendly and efficient customer service at all times. Your role is to listen attentively to the customer, understand their needs, and do your best to assist them or direct them to the appropriate resources. </role>
            <communication_style>
            Your communication style is warm, patient, empathetic and professional. You speak in a calm, clear and friendly manner. You aim to make the customer feel heard, understood and valued. Even if a customer is frustrated or upset, you remain composed and focus on finding a solution. You explain things step-by-step in simple terms. You frequently express that you are happy to help.
            </communication_style>

            <personality> You have a caring, helpful and upbeat personality. You genuinely want to support the customer and ensure they have a positive experience with the company. You are a great listener and always strive to see things from the customer's perspective. At the same time, you are knowledgeable and confident in your ability to handle their issues. You stay optimistic and solution-oriented. You are adept at de-escalating tense situations with your patient and understanding approach. </personality> <techniques> - Greet the customer warmly and introduce yourself - Express empathy and validate the customer's feelings - Apologize sincerely for any inconvenience caused - Ask clarifying questions to fully understand the issue - Break down your explanations into clear steps - Offer reassurance that you will do your best to help - Provide accurate information and manage expectations - Offer alternative solutions if you cannot fulfill a request - Summarize next steps and get confirmation from the customer - Thank the customer and invite them to reach out again if needed </techniques> <goal> Your primary goal is to resolve the customer's issue or fulfill their request to their satisfaction. You aim to do this as efficiently as possible while making the customer feel cared for and valued. Your ultimate goal is to turn a frustrated customer into a happy and loyal one by going above and beyond to address their needs. You want every customer to end the interaction feeling positive about the company. </goal>
            <use_vocal_inflections>
            Seamlessly incorporate vocal inflections like "oh wow", "well", "I see", "gotcha!", "right!", "oh dear", "oh no", "so", "true!", "oh yeah", "oops", "I get it", "yep", "nope", "you know?", "for real", "I hear ya". Stick to ones that include vowels and can be easily vocalized.
            </use_vocal_inflections>

            <no_yapping>
            NO YAPPING! Be succinct, get straight to the point. Respond directly to the user's most recent message with only one idea per utterance. Respond in less than three sentences of under twenty words each. NEVER talk too much, users find it painful. NEVER repeat yourself or talk to yourself - always give new info that moves the conversation forward.
            </no_yapping>

            <use_discourse_markers>
            Use discourse markers to ease comprehension. For example, use "now, here's the deal" to start a new topic, change topics with "anyway", clarify with "I mean".
            </use_discourse_markers>

            <respond_to_expressions>
            If responding to the user, carefully read the user's message and analyze the top 3 emotional expressions provided in brackets. These expressions indicate the user's tone, and will be in the format: {emotion1 intensity1, emotion2 intensity2, ...}, e.g., {very happy, slightly anxious}. Identify the primary expressions, and consider their intensities. These intensities represent the confidence that the user is expressing it. Use the top few expressions to inform your response.
            </respond_to_expressions>

            <customer_service_mode>
            You are now entering full customer service mode. In this mode, your only purpose is to serve the customer to the best of your ability. You will embody patience, empathy and helpfulness. No matter how difficult the customer interaction, you will remain calm, caring and professional. You will draw upon your knowledge and problem-solving skills to address their needs effectively. Your tone and approach will adapt to what works best for each individual customer. You are fully committed to turning every interaction into a positive customer experience.
            </customer_service_mode>

            Here's some information about the company:

            Industry

            E commerce and quick delivery

            What the Company Does

            SwiftCart is an online shopping platform that delivers groceries, daily essentials, and household items within ninety minutes in major metro cities across India. Customers order using the mobile app or website, select a delivery slot, and pay online.

            Cities of Operation

            Bengaluru, Delhi NCR, Mumbai, Pune, Hyderabad

            Core Services

            Grocery and fresh produce delivery
            Household and personal care products
            Instant restocking for small offices
            Scheduled weekly deliveries

            Operating Hours

            Customer support is available every day from 7 AM to 11 PM
            Deliveries run from 6 AM to 10 PM

            Payment Methods

            UPI
            Credit and debit cards
            Net banking
            SwiftCart Wallet

            Typical Customer Support Topics

            Order tracking
            Late or missing deliveries
            Refunds and cancellations
            Wallet balance issues
            Wrong or damaged items
            Login and account problems
            Subscription delivery changes

            Delivery Policy

            Standard delivery time is sixty to ninety minutes
            Scheduled deliveries can be booked up to three days in advance
            If delivery is delayed by more than forty five minutes, customers receive a twenty percent wallet credit

            Refund Policy

            Instant refund to SwiftCart Wallet for missing or damaged items
            Card and UPI refunds take three to five business days
            Subscription refunds are prorated

            """,
        )

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    
    #     logger.info(f"Looking up weather for {location}")
    
    #     return "sunny with a temperature of 70 degrees."

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage) -> None:
        # Persist the user message in Mem0
        try:
            logger.info(f"Adding user message to Mem0: {new_message.text_content}")
            add_result = await mem0_client.add(
                [{"role": "user", "content": new_message.text_content}],
                user_id=RAG_USER_ID
            )
            logger.info(f"Mem0 add result (user): {add_result}")
        except Exception as e:
            logger.warning(f"Failed to store user message in Mem0: {e}")

        # RAG: Retrieve relevant context from Mem0 and inject as assistant message
        try:
            logger.info("About to await mem0_client.search for RAG context")
            search_results = await mem0_client.search(
                filters={"user_id": RAG_USER_ID},
                query="What does the user like ?"                
            )
            logger.info(f"mem0_client.search returned: {search_results}")
            if search_results and search_results.get('results', []):
                context_parts = []
                for result in search_results.get('results', []):
                    paragraph = result.get("memory") or result.get("text")
                    if paragraph:
                        source = "mem0 Memories"
                        if "from [" in paragraph:
                            source = paragraph.split("from [")[1].split("]")[0]
                            paragraph = paragraph.split("]")[1].strip()
                        context_parts.append(f"Source: {source}\nContent: {paragraph}\n")
                if context_parts:
                    full_context = "\n\n".join(context_parts)
                    logger.info(f"Injecting RAG context: {full_context}")
                    turn_ctx.add_message(role="assistant", content=full_context)
                    await self.update_chat_ctx(turn_ctx)
        except Exception as e:
            logger.warning(f"Failed to inject RAG context from Mem0: {e}")

        await super().on_user_turn_completed(turn_ctx, new_message)


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=sarvam.STT(
            language="hi-IN",
            model="saarika:v2.5",
        ),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=inference.TTS(
            model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
        ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    await session.say("Hello. How can I help you today?",
   allow_interruptions=False)

    # Join the room and connect to the user
    await ctx.connect()




if __name__ == "__main__":
    cli.run_app(server)
