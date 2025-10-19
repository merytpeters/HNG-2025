function updateTimeinSec() {
  const timeElement = document.getElementById('user-time');
  const now = new Date();
  const timeinSeconds = 
    now.getHours() * 3600000 +
    now.getMinutes() * 60000 +
    now.getSeconds() * 1000 +
    now.getMilliseconds();
  timeElement.textContent = timeinSeconds;
}
setInterval(updateTimeinSec, 50);
updateTimeMsOnly();
