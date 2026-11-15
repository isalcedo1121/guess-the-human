// The six recordings and playback order match the original mockup.
const players = Object.fromEntries(
  ["correct", "wrong1", "wrong2", "wrong3", "win", "lose"].map(key => {
    const audio = new Audio(`/static/sounds/${key}.mp3`);
    audio.preload = "auto";
    return [key, audio];
  })
);
let wrongIndex = 0;
let unlocked = false;
let priming = null;

function stopAll() {
  for (const audio of Object.values(players)) {
    audio.pause();
    audio.currentTime = 0;
  }
}

// Call synchronously from a host button click, before awaiting the API.
export function unlockSounds() {
  if (unlocked || priming) return priming;
  priming = Promise.all(Object.values(players).map(async audio => {
    audio.muted = true;
    try {
      await audio.play();
      return true;
    } catch {
      return false;
    } finally {
      audio.pause();
      audio.currentTime = 0;
      audio.muted = false;
    }
  })).then(results => {
    unlocked = results.every(Boolean);
    priming = null;
  });
  return priming;
}

export async function playSound(key) {
  const audio = players[key];
  if (!audio) return;
  try {
    await priming;
    stopAll();
    await audio.play();
  } catch {
    // A blocked or unavailable sound never interrupts the game.
    unlocked = false;
  }
}

export function playWrong() {
  return playSound(`wrong${wrongIndex++ % 3 + 1}`);
}
