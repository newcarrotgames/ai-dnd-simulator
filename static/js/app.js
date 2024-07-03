function setActiveParticipant(index) {
	console.log("set active participant: " + index);
	// Mapping from index to element ID
	const idMapping = [
		'#dm .player-seat',
		'#p1 .player-seat',
		'#p2 .player-seat',
		'#p3 .player-seat'
	];

	// Check if the index is valid
	if (index < 0 || index >= idMapping.length) {
		console.warn(`Invalid index: ${index}. Must be between 0 and ${idMapping.length - 1}.`);
		return;
	}

	// First, remove the 'active-participant' class from all elements
	document.querySelectorAll('.player-seat').forEach(node => {
		node.classList.remove('active-participant');
	});

	// Get the ID corresponding to the index
	const id = idMapping[index];

	// Add the 'active-participant' class to the specified element
	const activeNode = document.querySelector(id);
	if (activeNode) {
		activeNode.classList.add('active-participant');
	} else {
		console.warn(`No element found with id: ${id}`);
	}
}

let mediaRecorder;
let audioChunks = [];
let players = [];

function updateConversation() {
	fetch('http://localhost:5000/conversation')
		.then(response => response.json())
		.then(data => {
			console.log(data);
			txt = "";
			data.forEach(line => {
				let speakerAndSpeech = line.split(":");
				if (speakerAndSpeech.length == 2)
					txt += "<p><strong>" + speakerAndSpeech[0] +"</strong>: " + speakerAndSpeech[1] + "</p>";
				else 
					txt += "<p>" + line + "</p>";
			});
			document.getElementById('conversation-log').innerHTML = txt;
		})
		.catch(error => {
			console.error('Error:', error);
		});
}

function askSinglePlayer(audioBlob, playerId) {
	const formData = new FormData();
	formData.append('audio', audioBlob, 'recording.webm');
	fetch('http://localhost:5000/mic', {
		method: 'POST',
		body: formData
	})
		.then(() => {
			setActiveParticipant(playerId);
			fetch(`http://localhost:5000/next_player/${playerId}`)
				.then(() => {
					setActiveParticipant(0);
					updateConversation();
				})
				.catch(error => console.error('Error sending audio to server:', error));
		})
		.catch(error => console.error('Error sending audio to server:', error));
}

function askAllPlayers(audioBlob) {
	const formData = new FormData();
	formData.append('audio', audioBlob, 'recording.webm');
	fetch('http://localhost:5000/mic', {
		method: 'POST',
		body: formData
	})
		.then(() => {
			// response = response.json();
			// return response;
			setActiveParticipant(1);
			fetch('http://localhost:5000/next_player/1')
				.then(() => {
					setActiveParticipant(2);
					fetch('http://localhost:5000/next_player/2')
						.then(() => {
							setActiveParticipant(3);
							fetch('http://localhost:5000/next_player/3')
								.then(() => { 
									setActiveParticipant(0);
									updateConversation();
								})
								.catch(error => console.error('Error sending audio to server:', error));
						})
						.catch(error => console.error('Error sending audio to server:', error));
				})
				.catch(error => console.error('Error sending audio to server:', error));
		})
		.catch(error => console.error('Error sending audio to server:', error));
}

async function getCharacterSheet(playerId) {
	// const response = await fetch('http://localhost:5000/sheet/' + playerId);
  	// const content = await response.json(); // or response.text(), response.blob(), etc.
  	// return content;

	const response = await fetch('http://localhost:5000/sheet/' + playerId);
	const content = await response.json(); // or response.json() if it's JSON data
	return content;
}

let init = async () => {
	players.push(await getCharacterSheet(1));
	players.push(await getCharacterSheet(2));
	players.push(await getCharacterSheet(3));
	console.log(players);
	document.querySelector('#p1 .player-name').textContent = players[0].characterName;
	document.querySelector('#p2 .player-name').textContent = players[1].characterName;
	document.querySelector('#p3 .player-name').textContent = players[2].characterName;

	setActiveParticipant(0);
	updateConversation();
	const micToggle = document.getElementById('micToggle');
	
	micToggle.addEventListener('click', async () => {
		if (micToggle.textContent === 'Unmute') {
			try {
				const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
				const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/ogg';
				mediaRecorder = new MediaRecorder(stream, { mimeType });

				mediaRecorder.ondataavailable = (event) => {
					audioChunks.push(event.data);
				};

				mediaRecorder.onstop = () => {
					const audioBlob = new Blob(audioChunks, { type: mimeType });
					askAllPlayers(audioBlob);
					audioChunks = [];
				};

				mediaRecorder.start();
				micToggle.textContent = 'Mute';
				micToggle.classList.add('muted');
			} catch (err) {
				console.error('Error accessing microphone:', err);
				alert('Unable to access the microphone. Please check your permissions.');
			}
		} else {
			mediaRecorder.stop();
			micToggle.textContent = 'Unmute';
			micToggle.classList.remove('muted');
		}
	});

	// Select all elements with the class 'node'
	const nodes = document.querySelectorAll('.receptive');

	// Add click event listener to each node
	nodes.forEach(node => {
		node.addEventListener('click', async function() {
			console.log('Clicked:', this.textContent);
			const playerId = this.dataset.playerId;
			console.log('player id: ', playerId);
			if (!this.classList.contains('muted')) {
				try {
					const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
					const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/ogg';
					mediaRecorder = new MediaRecorder(stream, { mimeType });
			
					mediaRecorder.ondataavailable = (event) => {
						audioChunks.push(event.data);
					};
			
					mediaRecorder.onstop = () => {
						const audioBlob = new Blob(audioChunks, { type: mimeType });
						askSinglePlayer(audioBlob, playerId);
						audioChunks = [];
					};
			
					mediaRecorder.start();
					this.classList.add('muted');
				} catch (err) {
					console.error('Error accessing microphone:', err);
					alert('Unable to access the microphone. Please check your permissions.');
				}
			} else {
				mediaRecorder.stop();
				this.classList.remove('muted');
			}
		});
	});

	// sounds
	const diceSound = document.getElementById('diceSound');
	diceSound.load();
};

function rollDie(sides) {
	diceSound.play();
	setTimeout(() => {
		const result = Math.floor(Math.random() * sides) + 1;
		document.getElementById('result').textContent = `You rolled a d${sides} and got: ${result}`;
	}, 1000);
}