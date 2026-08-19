const grid = document.getElementById('grid');
const colorPicker = document.getElementById('colorPicker');
const saveBtn = document.getElementById('saveBtn');
let isDrawing = false;

// --- 1. Generate the Drawing Grid ---
for (let i = 0; i < 256; i++) {
    const pixel = document.createElement('div');
    pixel.className = 'pixel';
    pixel.style.backgroundColor = "rgba(0,0,0,0)";
    
    pixel.addEventListener('mousedown', (e) => { isDrawing = true; e.target.style.backgroundColor = colorPicker.value; });
    pixel.addEventListener('mouseover', (e) => { if (isDrawing) e.target.style.backgroundColor = colorPicker.value; });
    
    grid.appendChild(pixel);
}

document.addEventListener('mouseup', () => { isDrawing = false; });

// --- 2. The Core Function: Save to PNG ---
saveBtn.addEventListener('click', () => {
    const canvas = document.getElementById('hiddenCanvas');
    const ctx = canvas.getContext('2d');
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const gridPixels = document.querySelectorAll('#grid .pixel');
    
    gridPixels.forEach((pixel, index) => {
        const color = pixel.style.backgroundColor;
        if (color === "rgba(0, 0, 0, 0)" || !color) return;

        const x = index % 16;
        const y = Math.floor(index / 16);

        ctx.fillStyle = color;
        ctx.fillRect(x, y, 1, 1);
    });

    const imageString = canvas.toDataURL("image/png");
    const downloadLink = document.createElement('a');
    downloadLink.href = imageString;
    downloadLink.download = 'mmos_cursor.png';
    
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
});
