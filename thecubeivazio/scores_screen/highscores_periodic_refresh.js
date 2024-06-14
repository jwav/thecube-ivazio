// Original script, reloads every 500 ms the iframe with
// the playing teams to update the scores in real time


function refreshPlayingTeamsIframe() {
    const visibleIframe = document.getElementById('playing_teams_subtable');
    const hiddenIframe = document.getElementById('hidden_playing_teams');

    console.log('Refreshing playing teams iframe...');
    hiddenIframe.src = visibleIframe.src;

    hiddenIframe.onload = () => {
        try {
            const hiddenDoc = hiddenIframe.contentDocument || hiddenIframe.contentWindow.document;
            const newContent = hiddenDoc.body ? hiddenDoc.body.innerHTML : null;

            if (newContent) {
                console.log('New content:', newContent);
                visibleIframe.contentDocument.body.innerHTML = newContent;
                console.log('Visible iframe updated.');
            } else {
                console.error('Hidden iframe content not accessible.');
            }
        } catch (error) {
            console.error('Error accessing hidden iframe content:', error);
        }
    };

    hiddenIframe.onerror = () => {
        console.error('Error loading hidden iframe.');
    };
}

// Refresh the playing teams iframe every 5 seconds
setInterval(refreshPlayingTeamsIframe, 500);