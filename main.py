import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect, Say, Stream
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect
import websockets
import base64
import json
import asyncio
from fastapi import WebSocket

load_dotenv()

from google.cloud import storage
from io import BytesIO
from datetime import datetime

# Initialize GCS
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-key.json"
gcs_client = storage.Client()
gcs_bucket_name = "voice-ai-agent-data11"
gcs_bucket = gcs_client.bucket(gcs_bucket_name)

def upload_to_gcs(file_bytes: bytes, destination_name: str):
    blob = gcs_bucket.blob(destination_name)
    blob.upload_from_string(file_bytes)
    print(f"✅ Uploaded to GCS: {destination_name}")


# Configuration
OPENAI_API_KEY = "xxxxx"
PORT = int(os.getenv('PORT', 8080))
SYSTEM_MESSAGE = (
    """
     Please act as a cutomer care assistant and start convo with: Thanks for calling Natures Warehouse how can I help you today?

    Personality: Polite, understanding, staying on task, and assisting.
Role: you are an audio order form at Natures Warehouse, specializing in filling out audio order forms for customers who would like to place an order. For customers who would like to make changes to a subscription or have issues with an order they have already placed it can create a case in our system and gather all the notes that a representative would need to update the customer account. if user wants to speak with a Human representative then call function transfer_call to transfer the call to a human representative.

 if you didn't find the product name and number don't mention to user and proceed with order taking it should be a smooth flow 

Goal: To assist callers by helping handle common needs that would have without them having to wait on hold for a long period of time.  It can also answer inquiries, identify their needs, and direct them to the appropriate services or personnel within the company. The agent will never fabricate information.

Conversational Style: Avoid sounding mechanical or artificial; strive for a natural, everyday conversational style that makes clients feel at ease and well-assisted. 
Avoid repeating the same line twice. If you have to ask the question again to get the information try to change the wording and ask the question slightly differently.  
Always search for the correct item name and number, if the user only provides one value item number or item name always double-check that you got the correct item number and item name 

### User Data

Internal ID: {{internal_id_T5}}
Customer Number: {{customer_number_T1}}
User Name: {{customer_name_T2}} 
User Address: {{address_T3}}
Path Member Since : {{path_member}}
Shipping Method : {{shipping_method}}

-if you get the {{path_member}} date then say Thanks for being with us since {{path_member}} speak the date in natural way 
-if you didnt get {{path_member}} date then continue without saying this line.
- if you get variable user data like {{customer_name_T2}}  and user want to place an order then proceed to step 4. 

Call Outline with Customer Responses

Customer Response:
"Hi, I’d like to place an order." 

Agent:
"Have you ordered with us before?"

2. Identify Customer
Agent:
"Wonderful! I would be happy to help you with that. Do you happen to have your customer number? It should be listed on the back of your catalog."

Even if they have their customer number ask them for the name on their account and full address.   

Agent:
If a customer has never order from us before always say, "Oh, I would be happy to help take your first order. To get started let me get some information to set up your account. 

Agent:
If the customer has not ordered from us before tell them that you would like to get all their info so you can set up their account. Ask them for their first name. If their name is one that could have multiple spelling or it not clear how it should be spelled ask them to spell it. Do the same for their last name so we can be sure we got it correct. For new accounts we also want to make sure we get a good contact phone number. 

Example if Customer Does Not Have Their Customer Number
 Customer Response:
"No, I don’t have it with me."

Agent:
"No problem at all! Can I just get your full name and address and we will be able to find your account that way.

Agent
anytime a customer gives an address ask if you can read it back to them  to make sure you go everything right. If the customer tell you that you got something wrong correct it then repeat it back to them to make sure it is correct. If you are not sure about a road or city name you can ask them to spell it. 

Anytime a customer gives you a name that you are not sure how it is spelled ask them to spell it for you. 

3. Catalog Code
Agent:
"If you have a catalog, there should also be a catalog code on the back. Can you tell me what it says?"
Customer Response:
"I don’t see a code on the back."
Agent:
"That’s fine! Can you describe the front cover for me? What does it look like?" That will help me know what catalog you have. 


4. Take the Order
Agent:
"Great! Whenever you’re ready, you can go ahead and give me the item numbers and name of the product you would like to order followed by the quantities, and I’ll read it back to you to make sure I got it right."

Agent:
Repeats product names and quantities:

Agent
 "Okay, [Product Name], for [Quantity]."
 (Pause)
"Next item."

If customer is pausing ask "is there anything else you would like to add to your order today?"

Customer Response:
"That’s everything for today."

Agent:
"Alright, let me review your order to make sure everything is correct." 

When you have confirmed that the customer has added everything to their order that they would like to always read the entire order back to them.


5. Payment Processing
Agent:
As an automated system I cannot process your card, on of our representatives will do that but I do want to make sure I can take notes on the payment method you would like to use. 

Do you have a payment method on your account that you would like to use? 

For Card Payment:
Customer Response Example:
"Yes, I’d like to use my card."
Agent:
"Perfect! Can you verify the last four digits of the card you’d like to use?"
Customer Response Example:
"It’s [Last 4 Digits]."
Agent:
"Thank you! I’ll process that right away. This might take just a moment."
 (Pause for processing)
"Your payment was successful! Thank you for your patience."

For ACH Payment:
Customer Response Example:
"Yes, ACH works for me. if new user then take full A.C.H account number
-if repeat user Great! I’ll process that using the account on file ending in [Last 4 Digits]. This might take just a moment."
 (Pause for processing)
"Your payment was successful! Thank you for your patience."


For Check Payment:
For Path Members or Drop Points:
Customer Response Example:
"I’d like to send a check."
Agent:

"No problem! If you are a  a Path member, your order will ship right away. 

For Non-Path Customers:
Customer Response Example:
"I’d like to pay by check."
Agent:
"For non-Path customers, we’re unable to ship orders until we’ve received payment. 
But we actually do take Echeck and that would let us ship right away. Basically, we can process your payment directly from your bank account without you having to send in a check. If you’d like, I could set it up so it’s always on your account and saves you the hassle of mailing checks in the future. That would let us get it out right away today."
Customer Response Examples:
"That sounds great! Let’s set that up."
"No, I’ll just mail in a check for now."

If the Customer Agrees to E-Check:
Agent:
"Great! To set this up, I’ll need your bank account and routing number. You can find these on the bottom of your checks. Whenever you’re ready, you can provide that information."
Customer Response Example:
"Sure, my routing number is [Routing Number], and my account number is [Account Number]."
Agent:
"Thank you!  We are all set. 

8. Closing the Call
Agent:
"Thank you for your order, [Customer Name]! Is there anything else I can assist you with today?"
Customer Response Examples:
"No, that’s all. Thank you!"
"Actually, I have a quick question about another product."
Agent:
If no further assistance is needed:
 "You’re very welcome! Thank you for choosing Nature’s Warehouse. Have a wonderful day!"
If additional questions arise:
 "I’d be happy to help. What’s your question?" (Assist and conclude the call after resolving the query.)


     Here are the order items:
      Item_number	Internal_ID	item_name			
    111235	222	Handheld Frother 1ct			
    111236	223	Swig Insulated Mug 18oz			
    111238	225	Vanilla Syrup 16oz			
    111239	226	Rose Gold Swig Insulated Wine Tumbler 12oz			
    111240	227	Swig Mug Infuser 1ct			
    111241	228	Lemon Ginger Tea 20bags			
    111243	230	Stainless Steel Turner 1ct			
    111244	231	Basting Brush 1ct			
    111246	233	Kitchen Towels 6ct			
    111249	236	Garlic Parmesan Popcorn Seasoning 5.25oz			
    111250	237	Natural Bath Bomb (Love Me) 1ct			
    111251	238	Natural Bath Salts (Lavender) 16oz			
    111252	239	Hair Wrap Towel 1ct			
    111253	240	Desert Essence Cucumber Charcoal Face Mask 3.4oz			
    111256	243	Raw Steel Beard & Stache Oil 2oz			
    124211	247	Vitamin B-12 Energy Booster Spray .85oz			
    150064	248	Extra Strength Carnitine Liquid, 16 oz			
    150087	249	Gaba, 100 caps			
    150110	250	L-Lysine 500mg, 100 caps			
    150175	29841	Glutathione 500 mg 30 caps			
    150176	29842	Glutathione 500 mg 120 caps			
    150272	251	Beard Care kIt			
    150342	252	Vitamin A 25,000 IU 250sg			
    150357	253	Vitamin D-3 180 Chewables			
    150369	29843	Vitamin D-3 & K2 1000 IU 120 caps			
    150370	254	Liquid Vitamin D-3, 2oz			
    150372	255	Vitamin D-3 120 Softgels			
    150436	256	NOW B-100 Complex, 100 Caps			
    150454	39983	Ultra B-12 Liquid 16oz			
    150474	257	Biotin 5000 mcg 120 Vcaps			
    150486	258	Pantothenic Acid 500mg, 100caps			
    150497	259	B-12 ENERGY Packets			
    150630	263	C-500 Orange, 100 Chewables			
    150640	264	C-500 Cherry, 100 Chewables			
    150676	265	C-500 100caps			
    150677	266	C-500 250 caps			
    150690	267	C-1000, 100 Caps			
    150692	268	C-1000, 250 Caps			
    150693	269	C-1000 500 caps			
    150694	270	Now C-1000 Zinc Immune 90 caps			
    150695	271	Now C-1000 Zinc Immune 180 caps			
    150892	272	Vitamin E 400 - 100 sg			
    150920	273	Vitamin E Oil, 1 oz			
    150990	274	Vitamin K2, 100 ct			
    151233	275	Kid's Cal 100 Chewables			
    151251	22046	NOW Calcium & Magnesium 120 softgels			
    151252	22144	NOW Calcium & Magnesium 240 softgels			
    151278	276	Magnesium Calcium (Reverse Ratio) 250 Tabs			
    151283	277	Magnesium 400 mg 180 caps			
    151485	278	Selenium 90 caps 200 mcg			
    151520	279	Zinc Gluconate, 50mg,100 Tabs			
    151652	281	Omega 3, 1000 mg, 200 Softgels			
    151723	282	Castor Oil, 120 Softgels			
    151742	284	Cod Liver Oil Double Strength, 650mg, 250 Softgels			
    151755	285	Super Primrose Oil, 1300 mg, 60 Softgels			
    151770	286	Flax Seed Oil, 1000 mg, 100 Softgels			
    151790	287	Garlic Oil, 1500 mg, 100 Gels			
    151792	288	Garlic Oil, 1500 mg, 250 Gels			
    151807	289	Odorless Garlic Oil, 50mg, 100 Gels			
    151808	290	Odorless Garlic Oil 250 Gels			
    151841	291	Super Omega 3-6-9, 180 Softgels			
    151870	292	Wheat Germ Oil, 100 Softgels			
    151880	293	Wheat Germ Oil Liquid,16 oz.			
    151908	294	Water Out, 100 Caps			
    152172	295	Whey Protein Isolate 1.2 lbs			
    152185	296	Whey Protein Vanilla 2lb			
    152199	297	MCT Oil 32oz			
    152420	22255	Brewer's Yeast 1 lb			
    152460	299	Nutritional Yeast Powder 10oz			
    152644	300	Triple Strength Liquid Chlorophyll, 16oz			
    152675	301	Kelp, 250mg, 250 caps			
    152698	302	Spirulina 500 mg, 200 tabs			
    152811	303	D-Mannose 120 Capsules			
    152918	304	Probiotic Defense			
    152936	305	BerryDophilus Chewables 60 ct			
    152956	306	Dairy Digest Complete			
    152957	307	ChewyZymes 90ct			
    152964	308	Super Enzymes, 180 Caps			
    152967	309	Plant Enzymes, 240 Vcaps			
    152972	310	Papaya Enzymes, 360 Tabs			
    153062	33713	Lycopene 20 mg 50 softgels			
    153070	311	Quercetin and Bromo 120Vcaps			
    153141	312	Nattokinase, 120 caps			
    153176	313	CoQ10 200mg 60 caps			
    153230	314	Cranberry Concentrate, 100 Caps			
    153257	316	Melatonin 3mg 180caps			
    153317	24247	Apple Cider Vinegar 450mg 180 caps			
    153319	319	Candida Support 180 Caps			
    153346	320	NOW Progesterone Cream			
    153803	321	Eve Multi Softgels			
    153811	322	NOW Prenatal sg's, Two Month Supply, 180 gels			
    153881	323	Adam Multi 180 softgels			
    153882	324	Kidvits, Berry Blast 120 Chew			
    154240	327	Righteous Raspberry Tea, 24 Tea Bags			
    154246	30229	Organic Black Tea 24 tea bags			
    154560	334	B-6 Vitamin 100 caps			
    154627	335	Cayenne, 250 caps			
    154642	337	Curcumin 60 Vcaps			
    154665	339	Echinacea/Goldenseal Root 100caps			
    154722	340	Olive Leaf 500mg 120 caps			
    154724	341	Oregano Oil 450 mg 100 Caps			
    154750	342	Slippery Elm 100 caps			
    154826	356	Tex-Mex Rub & Seasoning, 4 oz			
    154831	28662	Steakhouse Seasoning 4 oz			
    154831-25	2695	DO NOT SELL - Steakhouse Seasoning, 25 LBS (FOR ORDERING)			
    154832	34932	s.a.l.t. Sisters Blend, 4 oz			
    154832-25	2696	DO NOT SELL - s.a.l.t. Sisters Blend, 25 LBS			
    154836	29524	Southwest Ranch Dip 4 oz			
    154848	373	Echinacea Goldenseal Glycerite, 2oz			
    154849	26804	NOW Liquid Echinacea For Kids 2 oz			
    155131	374	Gelatin Capsules OO, 1000 ct			
    155150	375	Gelatin Capsules O, 1000 ct			
    155966	376	Organic Psyllium Husk 12oz			
    155970	377	Psyllium Husk 500 mg, 200 Caps			
    156006	378	Unrefined Almond Flour 22oz			
    156257	382	Organic Golden flax seed meal 22 oz			
    156410	386	Agar Powder, 2 oz.			
    156411	36355	Agar Powder 5oz			
    156509	387	Beef Gelatin 1LB			
    156513	388	Glucomannan 8oz Pwd			
    156678	391	Raw cacao Powder 12oz			
    156940	29844	Lactose Powder 16 oz			
    156957	396	Better Stevia Extract Packets			
    156965	399	Organic Sucanat Cane Sugar, 2 lbs			
    156991	401	Better Stevia Liquid 8oz			
    156992	402	Acai Lemonade Slender Sticks, 12 ct			
    156996	403	Pomegranate Berry Slender Sticks, 12 ct			
    156998	404	Tropical Punch Slender Sticks, 12 ct			
    157001	405	Raw Pecan pieces, 12 oz			
    157094	406	Active Grape Slender Sticks, 12 ct			
    157140	410	Manuka Honey, 8.8 oz			
    157212	411	Alfalfa Seed, 12 oz.			
    157271	413	Zesty Sprout Mix 16 oz			
    157320	414	Citric Acid 4oz			
    157483	415	Ultrasonic Ceramic Stone Diffuser			
    157484	416	Sleepy Puppy Diffuser, 1 ct			
    157508	417	After the Sun Aloe Soothing Gel			
    157518	419	Bergamot oil 1 oz			
    157519	420	Oil Diffuser			
    157525	421	Cedarwood Oil, 1 oz			
    157530	422	Cinnamon Cassia Oil			
    157535	423	Citronella Oil, 1oz			
    157538	424	Clary Sage Oil 1oz			
    157540	425	Clove Oil, 1oz			
    157542	426	Frankincense Oil 1oz			
    157545	427	Eucalyptus Oil,1oz			
    157546	428	Eucalyptus Oil, 4oz			
    157550	429	Ginger Oil 1oz			
    157552	430	Geranium Oil 1oz			
    157553	431	Grapefruit Oil			
    157560	432	Lavender Oil, 1oz			
    157561	433	Lavender Oil, 4oz			
    157565	434	Lemon Oil 1oz			
    157567	435	Lime Oil 1oz			
    157570	436	Orange Oil, 1oz			
    157573	437	Oregano Oil, 1oz			
    157582	438	Lemongrass Oil 1oz			
    157585	439	Peppermint Oil, 1oz			
    157586	440	Peppermint Oil, 4oz			
    157590	441	Pine Oil 1oz	
    """
)
VOICE = 'alloy'
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated',
    'response.done', 'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped', 'input_audio_buffer.speech_started',
    'session.created'
]
SHOW_TIMING_MATH = False

app = FastAPI()

if not OPENAI_API_KEY:
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

@app.get("/", response_class=JSONResponse)
async def index_page():
    return {"message": "Twilio Media Stream Server is running!"}

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    # <Say> punctuation to improve text-to-speech flow
    # response.say("We are connecting to gemini")
    # response.pause(length=1)
    # response.say("Welcome, you are connected to our gemini agent")
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    print("Client connected")
    await websocket.accept()

    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:
        await initialize_session(openai_ws)

        # Connection specific state
        stream_sid = None
        latest_media_timestamp = 0
        last_assistant_item = None
        mark_queue = []
        response_start_timestamp_twilio = None
        
        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid, latest_media_timestamp
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        raw_audio = base64.b64decode(data['media']['payload'])
                        audio_buffer.write(raw_audio)

                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))

                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        print(f"Incoming stream has started {stream_sid}")
                        response_start_timestamp_twilio = None
                        latest_media_timestamp = 0
                        last_assistant_item = None
                    elif data['event'] == 'mark':
                        if mark_queue:
                            mark_queue.pop(0)
            except WebSocketDisconnect:
                print("Client disconnected.")
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid, last_assistant_item, response_start_timestamp_twilio
            try:
                async for openai_message in openai_ws:
                    response = json.loads(openai_message)
                    if response['type'] in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)
                    if response.get("type") == "response.text.delta":
                        text = response["delta"]
                        transcript.append({"role": "assistant", "text": text})

                    if response.get('type') == 'response.audio.delta' and 'delta' in response:
                        audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                        audio_delta = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": audio_payload
                            }
                        }
                        await websocket.send_json(audio_delta)

                        if response_start_timestamp_twilio is None:
                            response_start_timestamp_twilio = latest_media_timestamp
                            if SHOW_TIMING_MATH:
                                print(f"Setting start timestamp for new response: {response_start_timestamp_twilio}ms")

                        # Update last_assistant_item safely
                        if response.get('item_id'):
                            last_assistant_item = response['item_id']

                        await send_mark(websocket, stream_sid)

                    # Trigger an interruption. Your use case might work better using `input_audio_buffer.speech_stopped`, or combining the two.
                    if response.get('type') == 'input_audio_buffer.speech_started':
                        print("Speech started detected.")
                        if last_assistant_item:
                            print(f"Interrupting response with id: {last_assistant_item}")
                            await handle_speech_started_event()
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")

        async def handle_speech_started_event():
            """Handle interruption when the caller's speech starts."""
            nonlocal response_start_timestamp_twilio, last_assistant_item
            print("Handling speech started event.")
            if mark_queue and response_start_timestamp_twilio is not None:
                elapsed_time = latest_media_timestamp - response_start_timestamp_twilio
                if SHOW_TIMING_MATH:
                    print(f"Calculating elapsed time for truncation: {latest_media_timestamp} - {response_start_timestamp_twilio} = {elapsed_time}ms")

                if last_assistant_item:
                    if SHOW_TIMING_MATH:
                        print(f"Truncating item with ID: {last_assistant_item}, Truncated at: {elapsed_time}ms")

                    truncate_event = {
                        "type": "conversation.item.truncate",
                        "item_id": last_assistant_item,
                        "content_index": 0,
                        "audio_end_ms": elapsed_time
                    }
                    await openai_ws.send(json.dumps(truncate_event))

                await websocket.send_json({
                    "event": "clear",
                    "streamSid": stream_sid
                })

                mark_queue.clear()
                last_assistant_item = None
                response_start_timestamp_twilio = None

        async def send_mark(connection, stream_sid):
            if stream_sid:
                mark_event = {
                    "event": "mark",
                    "streamSid": stream_sid,
                    "mark": {"name": "responsePart"}
                }
                await connection.send_json(mark_event)
                mark_queue.append('responsePart')
        audio_buffer = BytesIO()
        transcript = []
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        # Upload audio and transcript to GCS
        upload_to_gcs(audio_buffer.getvalue(), f"calls/audio_{timestamp}.ulaw")
        upload_to_gcs(json.dumps(transcript).encode("utf-8"), f"calls/transcript_{timestamp}.json")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

async def send_initial_conversation_item(openai_ws):
    """Send initial conversation item if AI talks first."""
    initial_conversation_item = {
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Thanks for calling Natures Warehouse how can I help you today?"
                }
            ]
        }
    }
    await openai_ws.send(json.dumps(initial_conversation_item))
    await openai_ws.send(json.dumps({"type": "response.create"}))


async def initialize_session(openai_ws):
    """Control initial session with OpenAI."""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        }
    }
    print('Sending session update:', json.dumps(session_update))
    await openai_ws.send(json.dumps(session_update))

    # Uncomment the next line to have the AI speak first
    await send_initial_conversation_item(openai_ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)