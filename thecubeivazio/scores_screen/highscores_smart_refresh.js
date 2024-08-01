function refreshSection(visibleId, hiddenId, url, isPlayingTeams = false) {
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
                if (isPlayingTeams) {
                    visibleDoc.body.innerHTML = newContent;
                } else {
                    const highscoreTable = hiddenDoc.querySelector('.highscore-table');
                    if (highscoreTable) {
                        visibleDoc.querySelector('.highscore-table').innerHTML = highscoreTable.innerHTML;
                    } else {
                        console.error(`Highscore table not found in hidden iframe for ${visibleId}.`);
                    }
                }
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

function refreshHighscores() {
    refreshSection('highscores_id_1', 'hidden_highscores_id_1', 'highscores_subtable_1.html');
    refreshSection('highscores_id_2', 'hidden_highscores_id_2', 'highscores_subtable_2.html');
    refreshSection('highscores_id_3', 'hidden_highscores_id_3', 'highscores_subtable_3.html');
}

document.addEventListener("DOMContentLoaded", function() {
    const eventSource = new EventSource('/stream');

    eventSource.onmessage = function(event) {
        if (event.data === 'refresh_playing_teams') {
            refreshSection('playing_teams_id', 'hidden_playing_teams_id', 'playing_teams_subtable.html', true);
        } else if (event.data === 'refresh_highscores') {
            refreshHighscores();
        }
    };

    eventSource.onerror = function(event) {
        console.error('EventSource failed:', event);
    };
});
