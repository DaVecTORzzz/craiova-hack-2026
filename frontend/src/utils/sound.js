// Sunet scurt pentru alerte CRITICAL conform specificațiilor din 03_C_frontend.pdf §4.3:
// "Adaugi evenimentul în listă și în KPI; toast + sunet scurt doar pentru CRITICAL."
// Implementat prin Web Audio API (zero dependențe externe, fără fișiere .mp3 care ar putea lipsi).

export function playCriticalAlertSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();

    // Ton 1: 880 Hz
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(880, ctx.currentTime);
    gain1.gain.setValueAtTime(0.15, ctx.currentTime);
    gain1.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.12);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start(ctx.currentTime);
    osc1.stop(ctx.currentTime + 0.12);

    // Ton 2: 1320 Hz
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(1320, ctx.currentTime + 0.14);
    gain2.gain.setValueAtTime(0.2, ctx.currentTime + 0.14);
    gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.28);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start(ctx.currentTime + 0.14);
    osc2.stop(ctx.currentTime + 0.28);
  } catch (e) {
    console.warn('AudioContext not allowed or not supported yet', e);
  }
}
