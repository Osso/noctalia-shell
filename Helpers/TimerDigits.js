.pragma library

function parseDigits(digits) {
  const text = String(digits || "").replace(/\D/g, "");
  const length = text.length;

  let seconds = 0;
  let minutes = 0;
  let hours = 0;

  if (length > 0) {
    seconds = parseInt(text.substring(Math.max(0, length - 2))) || 0;
  }
  if (length > 2) {
    minutes = parseInt(text.substring(Math.max(0, length - 4), length - 2)) || 0;
  }
  if (length > 4) {
    hours = parseInt(text.substring(0, length - 4)) || 0;
  }

  return {
    hours: Math.min(99, hours),
    minutes: Math.min(59, minutes),
    seconds: Math.min(59, seconds),
  };
}

function totalSecondsFromDigits(digits) {
  const time = parseDigits(digits);
  return (time.hours * 3600) + (time.minutes * 60) + time.seconds;
}

function formatParts(hours, minutes, seconds) {
  const paddedHours = hours.toString().padStart(2, "0");
  const paddedMinutes = minutes.toString().padStart(2, "0");
  const paddedSeconds = seconds.toString().padStart(2, "0");
  return `${paddedHours}:${paddedMinutes}:${paddedSeconds}`;
}

function formatFromDigits(digits) {
  const time = parseDigits(digits);
  return formatParts(time.hours, time.minutes, time.seconds);
}

function formatDuration(seconds, hideHoursWhenZero) {
  const totalSeconds = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;

  if (hideHoursWhenZero && hours === 0) {
    return `${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }

  return formatParts(hours, minutes, secs);
}
