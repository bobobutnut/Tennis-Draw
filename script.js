// Store player data
let playersData = [];
let myName = '';
let showingOpponents = false;

// DOM elements
const analyzeBtn = document.getElementById('analyzeBtn');
const drawUrlInput = document.getElementById('drawUrl');
const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const resultsDiv = document.getElementById('results');
const playerListDiv = document.getElementById('playerList');
const playerCountSpan = document.getElementById('playerCount');
const searchFilter = document.getElementById('searchFilter');
const sortFilter = document.getElementById('sortFilter');
const myNameInput = document.getElementById('myNameInput');
const findOpponentsBtn = document.getElementById('findOpponentsBtn');
const clearOpponentsBtn = document.getElementById('clearOpponentsBtn');
const myOpponentsInfo = document.getElementById('myOpponentsInfo');

// Event listeners
analyzeBtn.addEventListener('click', analyzeDraw);
searchFilter.addEventListener('input', filterAndDisplayPlayers);
sortFilter.addEventListener('change', filterAndDisplayPlayers);
findOpponentsBtn.addEventListener('click', findMyOpponents);
clearOpponentsBtn.addEventListener('click', clearOpponentsFilter);

async function analyzeDraw() {
    const url = drawUrlInput.value.trim();

    if (!url) {
        showError('Please enter a tournament draw URL');
        return;
    }

    // Show loading, hide others
    loadingDiv.classList.remove('hidden');
    errorDiv.classList.add('hidden');
    resultsDiv.classList.add('hidden');
    playersData = [];

    // Clear opponent finder
    clearOpponentsFilter();

    try {
        // Note: Due to CORS restrictions, we'll need to use a proxy
        // For demo purposes, I'll show the structure with sample data

        // In a real implementation, you'd need either:
        // 1. A backend server to proxy requests
        // 2. A CORS proxy service
        // 3. A browser extension to bypass CORS

        // For now, let's simulate with sample data
        await simulateDataFetch(url);

        // Display results
        playerCountSpan.textContent = playersData.length;

        // Populate autocomplete suggestions
        populatePlayerSuggestions();

        filterAndDisplayPlayers();
        resultsDiv.classList.remove('hidden');

    } catch (error) {
        showError('Error fetching draw data: ' + error.message);
    } finally {
        loadingDiv.classList.add('hidden');
    }
}

function populatePlayerSuggestions() {
    const datalist = document.getElementById('playerSuggestions');
    datalist.innerHTML = playersData
        .map(player => `<option value="${player.name}">`)
        .join('');
}

async function simulateDataFetch(url) {
    // Check if user wants to fetch real profile URLs
    const fetchProfiles = document.getElementById('fetchProfiles').checked;

    // Call our backend server
    const apiUrl = `http://localhost:5000/api/draw?url=${encodeURIComponent(url)}&fetch_profiles=${fetchProfiles}`;

    try {
        const response = await fetch(apiUrl);
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to fetch draw data');
        }

        playersData = data.players;

        if (playersData.length === 0) {
            throw new Error('No players found in draw');
        }

    } catch (error) {
        console.error('Error:', error);

        // Check if server is running
        if (error.message.includes('Failed to fetch')) {
            showError('⚠️ Backend server not running. Please start server.py first!\n\nIn terminal, run: python3 server.py');
        } else {
            showError('Error: ' + error.message);
        }

        throw error;
    }
}

function filterAndDisplayPlayers() {
    let filteredPlayers = [...playersData];

    // Apply search filter
    const searchTerm = searchFilter.value.toLowerCase();
    if (searchTerm) {
        filteredPlayers = filteredPlayers.filter(player =>
            player.name.toLowerCase().includes(searchTerm)
        );
    }

    // Apply sorting
    const sortBy = sortFilter.value;
    filteredPlayers.sort((a, b) => {
        switch(sortBy) {
            case 'name':
                return a.name.localeCompare(b.name);
            case 'ranking':
                return a.ranking - b.ranking;
            case 'wins':
                return b.wins - a.wins;
            default:
                return 0;
        }
    });

    // Display players
    displayPlayers(filteredPlayers);
}

function calculatePotentialOpponents(playerIndex, totalPlayers) {
    // Calculate potential opponents for next 2 rounds based on bracket structure
    // This assumes a standard single-elimination tournament bracket

    const opponents = [];

    // Find the bracket size (next power of 2)
    const bracketSize = Math.pow(2, Math.ceil(Math.log2(totalPlayers)));
    const position = playerIndex;

    // Round 1: Opponent in your immediate pair
    // In a bracket, position i is paired with position (bracketSize - 1 - i) in the same half
    const pairSize = bracketSize / Math.pow(2, 1); // Size of first round pairs
    const groupIndex = Math.floor(position / 2);
    const round1Start = groupIndex * 2;
    const round1End = round1Start + 2;

    for (let i = round1Start; i < round1End && i < totalPlayers; i++) {
        if (i !== position) {
            opponents.push({ index: i, round: 1 });
        }
    }

    // Round 2: Potential opponents from adjacent pair (winners would face each other)
    const groupOf4Index = Math.floor(position / 4);
    const round2Start = groupOf4Index * 4;
    const round2End = round2Start + 4;

    for (let i = round2Start; i < round2End && i < totalPlayers; i++) {
        if (i < round1Start || i >= round1End) {
            // This is in the adjacent pair for round 2
            opponents.push({ index: i, round: 2 });
        }
    }

    return opponents;
}

function findMyOpponents() {
    const searchName = myNameInput.value.trim();

    if (!searchName) {
        alert('Please enter your name');
        return;
    }

    // Find the player
    const myIndex = playersData.findIndex(p =>
        p.name.toLowerCase() === searchName.toLowerCase() ||
        p.name.toLowerCase().includes(searchName.toLowerCase())
    );

    if (myIndex === -1) {
        alert(`Player "${searchName}" not found in this draw`);
        return;
    }

    const me = playersData[myIndex];
    myName = me.name;
    showingOpponents = true;

    // Calculate potential opponents for next 2 rounds
    const potentialOpponents = calculatePotentialOpponents(myIndex, playersData.length);

    const round1Opponents = potentialOpponents.filter(o => o.round === 1);
    const round2Opponents = potentialOpponents.filter(o => o.round === 2);

    // Show info
    myOpponentsInfo.innerHTML = `
        <h4>✓ Found: ${myName}</h4>
        <p><strong>Next Round:</strong> ${round1Opponents.length} potential opponent(s)</p>
        <p><strong>Round 2:</strong> ${round2Opponents.length} potential opponent(s) (if you advance)</p>
        <p style="margin-top: 10px; color: #666; font-size: 0.9em;">Based on standard bracket structure</p>
    `;
    myOpponentsInfo.classList.remove('hidden');
    clearOpponentsBtn.classList.remove('hidden');

    // Store opponent indices for filtering
    window.opponentIndices = potentialOpponents;

    // Re-display with highlighting
    filterAndDisplayPlayers();
}

function clearOpponentsFilter() {
    myName = '';
    showingOpponents = false;
    myOpponentsInfo.classList.add('hidden');
    clearOpponentsBtn.classList.add('hidden');
    myNameInput.value = '';
    filterAndDisplayPlayers();
}

function displayPlayers(players) {
    if (players.length === 0) {
        playerListDiv.innerHTML = '<p style="text-align: center; color: #666;">No players found</p>';
        return;
    }

    // Filter to show only me and opponents if that mode is active
    let displayPlayers = players;
    if (showingOpponents && myName && window.opponentIndices) {
        const myIndex = playersData.findIndex(p => p.name === myName);
        const opponentIndicesSet = new Set(window.opponentIndices.map(o => o.index));

        displayPlayers = players.filter((p, idx) => {
            const originalIndex = playersData.findIndex(player => player.name === p.name);
            return originalIndex === myIndex || opponentIndicesSet.has(originalIndex);
        });
    }

    playerListDiv.innerHTML = displayPlayers.map(player => {
        const originalIndex = playersData.findIndex(p => p.name === player.name);
        const isMe = showingOpponents && player.name === myName;

        let opponentInfo = null;
        if (showingOpponents && !isMe && window.opponentIndices) {
            opponentInfo = window.opponentIndices.find(o => o.index === originalIndex);
        }

        let cardClass = 'player-card';
        if (isMe) cardClass += ' is-me';
        else if (opponentInfo && opponentInfo.round === 1) cardClass += ' is-opponent is-round1';
        else if (opponentInfo && opponentInfo.round === 2) cardClass += ' is-opponent is-round2';

        let badge = '';
        if (isMe) {
            badge = '<span class="player-badge badge-me">YOU</span>';
        } else if (opponentInfo) {
            if (opponentInfo.round === 1) {
                badge = '<span class="player-badge badge-round1">Next Round Opponent</span>';
            } else if (opponentInfo.round === 2) {
                badge = '<span class="player-badge badge-round2">Round 2 Opponent</span>';
            }
        }

        return `
            <div class="${cardClass}">
                ${badge}
                <div class="player-name">${player.name}</div>
                <div class="player-stats">
                    <div class="stat-row">
                        <span class="stat-label">Ranking</span>
                        <span class="stat-value ranking">${player.ranking}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Record</span>
                        <span class="stat-value">${player.wins}W - ${player.losses}L</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Win Rate</span>
                        <span class="stat-value">${player.winRate}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Last Match</span>
                        <span class="stat-value">${player.lastMatch}</span>
                    </div>
                </div>
                <a href="${player.profileUrl}" target="_blank" class="profile-link">View Full Profile →</a>
            </div>
        `;
    }).join('');
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    loadingDiv.classList.add('hidden');
    resultsDiv.classList.add('hidden');
}

// For actual implementation, here's the scraping logic structure:
/*
async function fetchDrawData(url) {
    // 1. Fetch the draw page HTML
    const drawResponse = await fetch(proxyUrl + url);
    const drawHtml = await drawResponse.text();

    // 2. Parse HTML to extract player links
    const parser = new DOMParser();
    const doc = parser.parseFromString(drawHtml, 'text/html');
    const playerLinks = doc.querySelectorAll('a[href*="/player/"]');

    // 3. Extract unique player URLs
    const uniquePlayers = new Set();
    playerLinks.forEach(link => uniquePlayers.add(link.href));

    // 4. Fetch each player's profile
    const playerPromises = Array.from(uniquePlayers).map(async (profileUrl) => {
        const response = await fetch(proxyUrl + profileUrl);
        const html = await response.text();
        return parsePlayerProfile(html, profileUrl);
    });

    playersData = await Promise.all(playerPromises);
}

function parsePlayerProfile(html, profileUrl) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    // Extract player statistics from the profile page
    // This will vary based on the actual HTML structure
    return {
        name: doc.querySelector('.player-name')?.textContent || 'Unknown',
        ranking: parseInt(doc.querySelector('.ranking')?.textContent) || 0,
        wins: parseInt(doc.querySelector('.wins')?.textContent) || 0,
        losses: parseInt(doc.querySelector('.losses')?.textContent) || 0,
        winRate: doc.querySelector('.win-rate')?.textContent || '0%',
        lastMatch: doc.querySelector('.last-match')?.textContent || 'N/A',
        profileUrl: profileUrl
    };
}
*/