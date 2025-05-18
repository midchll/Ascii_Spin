fetch ('ascii_frames.json')
    .then(res => res.json())
    .then(frames => {
        let index = 0;
        const frameElement = document.getElementById('ascii-frame');

        setInterval(() => {
            frameElement.textContent = frames[index];
            index = (index + 1) % frames.length;
        }, 50);
    });