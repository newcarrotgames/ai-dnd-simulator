import os
import random
import tempfile
import pygame
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from openai import OpenAI
from gtts import gTTS
from werkzeug.utils import secure_filename
from pydub import AudioSegment

pygame.mixer.init()

app = Flask(__name__, static_folder='static')
CORS(app)  # This allows CORS for all domains on all routes

# Enable debug mode
app.config['DEBUG'] = True

# Ensure templates are auto-reloaded
app.config['TEMPLATES_AUTO_RELOAD'] = True

# config audio uploads
UPLOAD_FOLDER = 'audio_uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
	return '.' in filename and \
		   filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

DM = 0
P1 = 1
P2 = 2
P3 = 3

QUESTION_PROMPT = "Here is the conversation so far. Please respond as a human player would but try to keep your responses short.\n\n"
client = OpenAI()

conversation = []

# def tts(voice_id, text):
# 	tts = gTTS(text, lang='en', tld='com.au')
# 	mp3_filename = os.path.dirname(__file__) + "\\mp3s\\" + str(random.randint(0, 999999)) + ".mp3"
# 	tts.save(mp3_filename)
# 	playsound(mp3_filename)

def load_text_file(file_path):
	"""
	Loads a text file from the given file path and returns its content as a string.
	
	Args:
	file_path (str): The path to the text file to be read.
	
	Returns:
	str: The content of the text file as a string.
	
	Raises:
	FileNotFoundError: If the specified file is not found.
	IOError: If there's an error reading the file.
	"""
	try:
		with open(file_path, 'r', encoding='utf-8') as file:
			content = file.read()
		return content
	except FileNotFoundError:
		print(f"Error: The file at {file_path} was not found.")
		raise
	except IOError as e:
		print(f"Error reading the file: {e}")
		raise

player_1_sheet = load_text_file("player1.json")
player_2_sheet = load_text_file("player2.json")
player_3_sheet = load_text_file("player3.json")

PLAYER_PROMPT = "Please respond to the DM's requests as a human player would.\n\n"
PLAYER_1_PROMPT = "You are player 1 in a group of three players currently playing DND. " + PLAYER_PROMPT + " Here is your character sheet:\n\n" + player_1_sheet
PLAYER_2_PROMPT = "You are player 2 in a group of three players currently playing DND. " + PLAYER_PROMPT + " Here is your character sheet:\n\n" + player_2_sheet
PLAYER_3_PROMPT = "You are player 3 in a group of three players currently playing DND. " + PLAYER_PROMPT + " Here is your character sheet:\n\n" + player_3_sheet

# def tts(voice_id, text):
# 	tld = 'us'
# 	if int(voice_id) == 2:
# 		tld = 'co.uk'
# 	elif int(voice_id) == 3:
# 		tld = 'com.au'
# 	print(f"voice_id: {voice_id}, tld: {tld}")
# 	tts = gTTS(text, lang="en", slow=False, tld=tld)
	
# 	tts.save(mp3_filename)
# 	print("mp3_filename: " + "./mp3s/" + os.path.basename(mp3_filename))
# 	# Load and play the MP3 file
# 	pygame.mixer.music.load(mp3_filename)
# 	pygame.mixer.music.play()
	
# 	# Wait for the audio to finish playing
# 	while pygame.mixer.music.get_busy():
# 		pygame.time.Clock().tick(10)
  
def tts(voice_id, text):
	voice = 'echo'
	if int(voice_id) == 2:
		voice = 'onyx'
	elif int(voice_id) == 3:
		voice = 'fable'
	print(f"voice_id: {voice_id}, voice: {voice}")
	mp3_filename = os.path.join(os.path.dirname(__file__), "mp3s", f"{random.randint(0, 999999)}.mp3")
	with client.audio.speech.with_streaming_response.create(
		model="tts-1",
		voice=voice,
		input=text
	) as response:
		response.stream_to_file(mp3_filename)
  
	# Load and play the MP3 file
	print("mp3_filename: " + "./mp3s/" + os.path.basename(mp3_filename))
	pygame.mixer.music.load(mp3_filename)
	pygame.mixer.music.play()
	
	# Wait for the audio to finish playing
	while pygame.mixer.music.get_busy():
		pygame.time.Clock().tick(10)

def convert_to_mp3(input_file, output_file):
	audio = AudioSegment.from_file(input_file)
	audio.export(output_file, format="mp3")
	
def convert_to_wav(input_file):
	audio = AudioSegment.from_file(input_file)
	with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
		audio.export(temp_wav.name, format="wav")
		return temp_wav.name

def speech_to_text(audio_filename):
	try:
		audio_file = open(audio_filename, "rb")
		transcription = client.audio.transcriptions.create(
			model="whisper-1",
			file=audio_file
		)
		print(transcription)
		return transcription.text
	except Exception as e:
		return "Speech Recognition could not understand the audio, error: " + str(e)

def get_question():
	global conversation
	return QUESTION_PROMPT + "\n\n".join(conversation)

def get_substring_after_last_colon(text):
    """
    Returns a substring of everything after the last colon in the given string.
    If there is no colon, returns the original string.

    Args:
    text (str): The input string to process.

    Returns:
    str: The substring after the last colon, or the original string if no colon is found.
    """
    # Find the position of the last colon
    last_colon_index = text.rfind(':')
    
    # If a colon is found, return everything after it (stripped of leading/trailing whitespace)
    if last_colon_index != -1:
        return text[last_colon_index + 1:].strip()
    else:
        # If no colon is found, return the original string (stripped of leading/trailing whitespace)
        return text.strip()

def filter_message(message):
    m = get_substring_after_last_colon(message)
    m = m.replace("\"", "", -1)
    m = m.replace("*", "", -1)
    return m

def ask_player(player_id):
	global conversation

	system_prompt = ""
	if str(player_id) == "1":
		system_prompt = PLAYER_1_PROMPT
	elif str(player_id) == "2":
		system_prompt = PLAYER_2_PROMPT
	elif str(player_id) == "3":
		system_prompt = PLAYER_3_PROMPT
	else:
		return jsonify({'error': 'Player ID is required and must be 1, 2, or 3'}), 400
	print(f"asking player {player_id} for next actions")
	
	completion = client.chat.completions.create(
		model="gpt-4o",
		messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": get_question()}
		]
	)
	message = filter_message(completion.choices[0].message.content)
	print(f"player {player_id} said: {message}")
	if "NULL" in message:
		print(f"player {player_id} declined to say anything")
		return
	conversation.append(f"Player {player_id}: {message}")
	tts(player_id, str(message))


## ROUTES ################################################################################################

# #- /player/<player_id> -----------------------------------------------------------------------------------

# @app.route('/player/<player_id>', methods=['POST'])
# def player(player_id):
# 	global client
	
# 	data = request.json
# 	user_prompt = data.get('prompt', '')

# 	if not user_prompt:
# 		return jsonify({'error': 'Prompt is required'}), 400
	
# 	system_prompt = ""
# 	if player_id == "1":
# 		system_prompt = PLAYER_1_PROMPT
# 	elif player_id == "2":
# 		system_prompt = PLAYER_1_PROMPT
# 	elif player_id == "3":
# 		system_prompt = PLAYER_1_PROMPT
# 	else:
# 		return jsonify({'error': 'Player ID is required and must be 1, 2, or 3'}), 400
 
# 	completion = client.chat.completions.create(
# 		model="gpt-3.5-turbo",
# 		messages=[
# 			{"role": "system", "content": system_prompt},
# 			{"role": "user", "content": user_prompt}
# 		]
# 	)
# 	message = completion.choices[0].message
# 	tts(player_id, str(message.content))
# 	return message.content

#- /mic -------------------------------------------------------------------------------------------

@app.route('/mic', methods=['POST'])
def receive_audio():
	global conversation
	
	if 'audio' not in request.files:
		return jsonify({'error': 'No audio file part'}), 400
	
	file = request.files['audio']
	
	if file.filename == '':
		return jsonify({'error': 'No selected file'}), 400
	
	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
		file.save(file_path)
		dm_text = speech_to_text(file_path)
		print("DM said: " + dm_text)
		conversation.append("Dungeon Master: " + dm_text)
		return jsonify({'message': 'Audio received and processed', 'filename': filename}), 200
	
	return jsonify({'error': 'File type not allowed'}), 400

#- /next_player/<player_id> -----------------------------------------------------------------------

@app.route('/next_player/<player_id>', methods=['GET'])
def next_player(player_id):
	ask_player(player_id)
	return jsonify({})

#- /conversation ----------------------------------------------------------------------------------

@app.route('/conversation')
def conversation_log():
	global conversation

	return jsonify(conversation)

#- /sheet -----------------------------------------------------------------------------------------

@app.route('/sheet/<player_id>')
def sheet(player_id):
	global player_1_sheet
	global player_2_sheet
	global player_3_sheet

	id = int(player_id)
	print(f"sheet() - player id: {player_id}, id: {id}")
	if id == 1:
		return player_1_sheet
	elif id == 2:
		return player_2_sheet
	elif id == 3:
		return player_3_sheet
	else:
		return "{\"error\": \"Unrecognized player ID\"}"

#- / ----------------------------------------------------------------------------------------------

@app.route('/')
def home():
	return render_template('index.html')

## ROUTES END #####################################################################################

if __name__ == '__main__':
	app.run(debug=True)

