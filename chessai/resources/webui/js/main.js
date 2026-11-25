"use strict";

let intervalID;

function update() {
    fetch("/api/update", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: "{}",
    }).then((response) => response.json()).then((body) => {
        document.querySelector(".image-area img").src = body.image_url;
        if (body.state.game_over) {
            clearInterval(intervalID);
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    fetch("/api/init", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"})
        .then((response) => response.json())
        .then((body) => {
            document.title = body.title;
            intervalID = setInterval(update, 50);
            update();
        });
});
