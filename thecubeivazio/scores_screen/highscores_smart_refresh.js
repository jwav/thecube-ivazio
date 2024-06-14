function refreshSection(visibleId, hiddenId, url) {
    const visibleIframe = document.getElementById(visibleId);
    const hiddenIframe = document.getElementById(hiddenId);

    if (!visibleIframe) {
        console.error(`Visible iframe with id ${visibleId} not found`);
        return;
    }

    if (!hiddenIframe) {
        console.error(`Hidden iframe with id ${hiddenId} not found`);
        return;
    }

    hiddenIframe.src = url;

    hiddenIframe.onload = () => {
        try {
            const hiddenDoc = hiddenIframe.contentDocument || hiddenIframe.contentWindow.document;
            const newContent = hiddenDoc.body ? hiddenDoc.body.innerHTML : null;

            if (newContent) {
                const visibleDoc = visibleIframe.contentDocument || visibleIframe.contentWindow.document;
                visibleDoc.body.innerHTML = newContent;
            } else {
                console.error(`Hidden iframe content not accessible for ${visibleId}.`);
            }
        } catch (error) {
            console.error(`Error accessing hidden iframe content for ${visibleId}:`, error);
        }
    };

    hiddenIframe.onerror = () => {
        console.error(`Error loading hidden iframe for ${visibleId}.`);
    };
}

document.addEventListener("DOMContentLoaded", function() {
    const eventSource = new EventSource('/stream');

    eventSource.onmessage = function(event) {
        if (event.data === 'refresh_playing_teams') {
            refreshSection('playing_teams_subtable', 'hidden_playing_teams', 'playing_teams_subtable.html');
        } else if (event.data === 'refresh_highscores') {
            refreshSection('highscores', 'hidden_highscores', 'highscores_main.html');
        }
    };

    eventSource.onerror = function(event) {
        console.error('EventSource failed:', event);
    };
});
