const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('capture');
const resultDiv = document.getElementById('result');

async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
  } catch (err) {
    resultDiv.textContent = 'Camera access denied: ' + err.message;
  }
}

function analyzeImage() {
  const context = canvas.getContext('2d');
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
  let r = 0, g = 0, b = 0;
  for (let i = 0; i < data.length; i += 4) {
    r += data[i];
    g += data[i + 1];
    b += data[i + 2];
  }
  const pixelCount = data.length / 4;
  r /= pixelCount;
  g /= pixelCount;
  b /= pixelCount;
  const brightness = (r + g + b) / 3;

  let recommendation = '';
  if (r > g + 20 && r > b + 20) {
    recommendation = 'Your skin appears slightly red. Consider using a soothing cream with aloe.';
  } else if (brightness < 80) {
    recommendation = 'Your skin looks a bit dry. Try a hydrating moisturizer rich in hyaluronic acid.';
  } else {
    recommendation = 'Your skin tone looks balanced. Maintain it with a gentle daily cleanser and SPF.';
  }

  resultDiv.textContent = recommendation;
}

captureBtn.addEventListener('click', () => {
  canvas.style.display = 'block';
  analyzeImage();
});

initCamera();
