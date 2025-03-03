let currentTaskId = null;
const pollInterval = 2000; // 2 seconds

async function submitResearch(event) {
    event.preventDefault();
    
    const query = document.getElementById('query').value;
    const submitButton = document.getElementById('submitBtn');
    const statusText = document.getElementById('statusText');
    const resultsDiv = document.getElementById('results');
    
    // Clear previous results
    resultsDiv.innerHTML = '';
    statusText.innerHTML = '';
    
    // Show loading state
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading"></span>Researching...';
    
    try {
        const response = await fetch('/research', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentTaskId = data.task_id;
            statusText.textContent = 'Research in progress...';
            pollResults();
        } else {
            throw new Error(data.error || 'Failed to start research');
        }
    } catch (error) {
        statusText.innerHTML = `<div class="error">${error.message}</div>`;
        submitButton.disabled = false;
        submitButton.textContent = 'Submit';
    }
}

async function pollResults() {
    if (!currentTaskId) return;
    
    try {
        const response = await fetch(`/status/${currentTaskId}`);
        const data = await response.json();
        
        if (data.status === 'completed') {
            const resultsResponse = await fetch(`/results/${currentTaskId}`);
            const results = await resultsResponse.json();
            displayResults(results);
            currentTaskId = null;
            
            // Reset button state
            const submitButton = document.getElementById('submitBtn');
            submitButton.disabled = false;
            submitButton.textContent = 'Submit';
        } else if (data.status === 'processing') {
            setTimeout(pollResults, pollInterval);
        } else {
            throw new Error('Research failed');
        }
    } catch (error) {
        const statusText = document.getElementById('statusText');
        statusText.innerHTML = `<div class="error">${error.message}</div>`;
        
        // Reset button state
        const submitButton = document.getElementById('submitBtn');
        submitButton.disabled = false;
        submitButton.textContent = 'Submit';
        
        currentTaskId = null;
    }
}

function displayResults(results) {
    const resultsDiv = document.getElementById('results');
    const statusText = document.getElementById('statusText');
    
    statusText.textContent = 'Research completed!';
    
    let html = '<div class="results">';
    
    // Display summary
    if (results.summary) {
        html += `<h3 class="text-xl font-semibold mb-4">Summary</h3>
                 <p class="mb-4">${results.summary}</p>`;
    }
    
    // Display key points
    if (results.key_points && results.key_points.length > 0) {
        html += `<h3 class="text-xl font-semibold mb-2">Key Points</h3>
                 <ul class="list-disc pl-5 mb-4">`;
        results.key_points.forEach(point => {
            html += `<li class="mb-1">${point}</li>`;
        });
        html += '</ul>';
    }
    
    // Display sources
    if (results.sources && results.sources.length > 0) {
        html += `<h3 class="text-xl font-semibold mb-2">Sources</h3>
                 <ul class="list-decimal pl-5">`;
        results.sources.forEach(source => {
            html += `<li class="mb-1"><a href="${source}" class="text-blue-600 hover:underline" target="_blank">${source}</a></li>`;
        });
        html += '</ul>';
    }
    
    html += '</div>';
    resultsDiv.innerHTML = html;
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('researchForm');
    form.addEventListener('submit', submitResearch);
});
