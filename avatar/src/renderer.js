const ipcRenderer = (window.api && typeof window.api.send === 'function')
  ? { send: window.api.send, on: window.api.on }
  : { send: () => {}, on: () => {} }

const windowControls = window.windowControls || {
  moveWindowDelta: () => {},
  setIgnoreMouse: () => {},
  moveWindow: () => {},
}

const canvas = document.getElementById('c')
const ctx    = canvas.getContext('2d')
const CX = 100
const CY = 105

// ── STATE ─────────────────────────────────────────────────────────────────────
const state = {
  happiness: 60, trust: 40, energy: 75, attachment: 20,
  animState: 'idle', amplitude: 0, targetAmp: 0,
  breathe: 0, squishY: 1.0, squishX: 1.0,
  bounce: 0, wobble: 0,
  blinkT: 0, nextBlink: 3, blinkVal: 0,
  lookX: 0, lookY: 0, targetLookX: 0, targetLookY: 0, nextLook: 2,
  thinkDot: 0,
  // Reaction system
  reactionT: 0, reactionType: null,
  // Mood transition
  moodT: 1, prevMood: 'neutral', targetMood: 'neutral', currentMood: 'neutral',
  // Interpolated face params
  eyeSquint: 0, eyeDrop: 0, eyeWide: 0,
  mouthCurve: 0, blushAmt: 0, tearAmt: 0,
  browAngle: 0,
}

// ── MOOD DEFINITIONS ──────────────────────────────────────────────────────────
const MOODS = {
  happy:     { body:'#FFD166', glow:'#FFB347', pupil:'#7B3F00', iris:'#FF8C00',
               eyeSquint:0.35, eyeDrop:0,   eyeWide:0,   mouthCurve:1.2,  blush:0.55, tear:0,   browAngle:-0.18 },
  excited:   { body:'#FF6B9D', glow:'#FF4081', pupil:'#5C0020', iris:'#FF1493',
               eyeSquint:0.5,  eyeDrop:0,   eyeWide:0.2, mouthCurve:2.0,  blush:0.85, tear:0,   browAngle:-0.28 },
  neutral:   { body:'#7EC8E3', glow:'#00AACC', pupil:'#1A3A4A', iris:'#0088BB',
               eyeSquint:0,    eyeDrop:0,   eyeWide:0,   mouthCurve:0,    blush:0,    tear:0,   browAngle:0 },
  thinking:  { body:'#A8DADC', glow:'#457B9D', pupil:'#1D3557', iris:'#457B9D',
               eyeSquint:0.1,  eyeDrop:0,   eyeWide:0,   mouthCurve:-0.1, blush:0,    tear:0,   browAngle:0.22 },
  sad:       { body:'#8896AB', glow:'#5C677D', pupil:'#2D3142', iris:'#5C677D',
               eyeSquint:0,    eyeDrop:0.6, eyeWide:0,   mouthCurve:-1.2, blush:0,    tear:0.8, browAngle:0.42 },
  surprised: { body:'#C77DFF', glow:'#9B5DE5', pupil:'#3D0060', iris:'#7B2FBE',
               eyeSquint:0,    eyeDrop:0,   eyeWide:0.9, mouthCurve:0.3,  blush:0.3,  tear:0,   browAngle:-0.52 },
}

const lerp  = (a, b, t) => a + (b - a) * t
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))

// ── MOOD TRANSITION ───────────────────────────────────────────────────────────
function setMood(m) {
  if (m === state.targetMood) return
  state.prevMood   = state.currentMood
  state.targetMood = m
  state.moodT      = 0
}

function updateMoodTransition(dt) {
  if (state.moodT >= 1) return
  state.moodT = clamp(state.moodT + dt * 2.5, 0, 1)
  const t = state.moodT * state.moodT * (3 - 2 * state.moodT) // smoothstep
  const A = MOODS[state.prevMood]   || MOODS.neutral
  const B = MOODS[state.targetMood] || MOODS.neutral
  state.currentMood = state.targetMood
  state.eyeSquint   = lerp(A.eyeSquint,  B.eyeSquint,  t)
  state.eyeDrop     = lerp(A.eyeDrop,    B.eyeDrop,    t)
  state.eyeWide     = lerp(A.eyeWide,    B.eyeWide,    t)
  state.mouthCurve  = lerp(A.mouthCurve, B.mouthCurve, t)
  state.blushAmt    = lerp(A.blush,      B.blush,      t)
  state.tearAmt     = lerp(A.tear,       B.tear,       t)
  state.browAngle   = lerp(A.browAngle,  B.browAngle,  t)
}

function computeMood() {
  const h = state.happiness, e = state.energy
  if (state.animState === 'thinking') return 'thinking'
  if (h > 75 && e > 60) return 'excited'
  if (h > 55)           return 'happy'
  if (h < 35)           return 'sad'
  if (e > 85)           return 'surprised'
  return 'neutral'
}

// ── REACTION SYSTEM ───────────────────────────────────────────────────────────
function triggerReaction(type) {
  state.reactionType = type
  state.reactionT    = 0
}

function updateReaction(dt) {
  if (!state.reactionType) return
  state.reactionT += dt
  const t = state.reactionT

  if (state.reactionType === 'happy_jump') {
    if      (t < 0.12) { state.squishY = lerp(1.0, 0.62, t/0.12);  state.squishX = lerp(1.0, 1.38, t/0.12);  state.bounce = 0 }
    else if (t < 0.28) { const p=(t-0.12)/0.16; state.squishY=lerp(0.62,1.5,p);  state.squishX=lerp(1.38,0.70,p); state.bounce=lerp(0,-30,p) }
    else if (t < 0.44) { const p=(t-0.28)/0.16; state.squishY=lerp(1.5,1.1,p);   state.squishX=lerp(0.70,0.95,p); state.bounce=lerp(-30,-12,p) }
    else if (t < 0.60) { const p=(t-0.44)/0.16; state.squishY=lerp(1.1,0.78,p);  state.squishX=lerp(0.95,1.20,p); state.bounce=lerp(-12,0,p) }
    else if (t < 0.78) { const p=(t-0.60)/0.18; state.squishY=lerp(0.78,1.04,p); state.squishX=lerp(1.20,0.98,p) }
    else { state.squishY=1; state.squishX=1; state.bounce=0; state.reactionType=null }
  }

  else if (state.reactionType === 'sad_droop') {
    if      (t < 0.35) { state.squishY=lerp(1.0,0.85,t/0.35); state.squishX=lerp(1.0,1.12,t/0.35); state.bounce=lerp(0,9,t/0.35) }
    else if (t < 0.65) { state.wobble = Math.sin(t * 38) * 0.055 }
    else if (t < 1.0)  { state.wobble=0 }
    else { state.squishY=1; state.squishX=1; state.bounce=0; state.wobble=0; state.reactionType=null }
  }

  else if (state.reactionType === 'surprise_pop') {
    if      (t < 0.08) { state.squishY=lerp(1.0,1.55,t/0.08); state.squishX=lerp(1.0,0.68,t/0.08) }
    else if (t < 0.22) { const p=(t-0.08)/0.14; state.squishY=lerp(1.55,0.90,p); state.squishX=lerp(0.68,1.08,p) }
    else if (t < 0.36) { const p=(t-0.22)/0.14; state.squishY=lerp(0.90,1.04,p); state.squishX=lerp(1.08,0.97,p) }
    else { state.squishY=1; state.squishX=1; state.reactionType=null }
  }

  else if (state.reactionType === 'excited_bounce') {
    if (t < 0.85) {
      const fade = 1 - t/0.85
      state.bounce  = Math.sin(t * Math.PI * 5.5) * -20 * fade
      state.squishY = 1 + Math.sin(t * Math.PI * 5.5) * 0.20 * fade
      state.squishX = 1 - Math.sin(t * Math.PI * 5.5) * 0.13 * fade
    } else { state.bounce=0; state.squishY=1; state.squishX=1; state.reactionType=null }
  }

  else if (state.reactionType === 'thinking_tilt') {
    if      (t < 0.25) { state.wobble = lerp(0, 0.20, t/0.25) }
    else if (t < 2.0)  { state.wobble = 0.20 }
    else { state.wobble=0; state.reactionType=null }
  }
}

// ── CONTINUOUS MOOD BODY ──────────────────────────────────────────────────────
function updateMoodBody(t) {
  if (state.reactionType) return
  switch (state.currentMood) {
    case 'happy':
      state.bounce  = Math.sin(t * 2.2) * 6
      state.wobble  = Math.sin(t * 1.8) * 0.04
      state.squishY = 1 + Math.sin(t * 2.2) * 0.04
      state.squishX = 1 - Math.sin(t * 2.2) * 0.025
      break
    case 'excited':
      state.bounce  = Math.sin(t * 5.2) * 9
      state.wobble  = Math.sin(t * 4.8) * 0.08
      state.squishY = 1 + Math.sin(t * 5.2) * 0.08
      state.squishX = 1 - Math.sin(t * 5.2) * 0.055
      break
    case 'sad':
      state.bounce  = Math.sin(t * 0.65) * 3 + 6
      state.wobble  = Math.sin(t * 0.45) * 0.012
      state.squishY = 0.91 + Math.sin(t * 0.65) * 0.018
      state.squishX = 1.07
      break
    case 'surprised':
      state.bounce  = Math.sin(t * 3.8) * 4
      state.wobble  = Math.sin(t * 6.5) * 0.055
      break
    case 'thinking':
      state.bounce  = Math.sin(t * 0.9) * 3
      state.wobble  = 0.16 + Math.sin(t * 0.55) * 0.02
      state.squishY = 1.0; state.squishX = 1.0
      break
    default:
      state.bounce  = Math.sin(t * 1.1) * 5
      state.wobble  = Math.sin(t * 0.8) * 0.03
      state.squishY = 1.0; state.squishX = 1.0
  }
}

// ── DRAW ──────────────────────────────────────────────────────────────────────
function draw(dt) {
  ctx.clearRect(0, 0, 200, 200)
  const mood = MOODS[state.currentMood] || MOODS.neutral
  const amp  = state.amplitude
  const t    = performance.now() / 1000

  state.breathe += dt * (state.animState === 'talking' ? 9 : 1.3)
  const breathe = 1 + Math.sin(state.breathe) * 0.022
  const R  = 52 * breathe * state.squishX
  const RY = 52 * breathe * state.squishY
  const by = state.bounce + CY

  // Glow
  const glowR = 76 + amp * 24 + (state.currentMood === 'excited' ? 10 : 0)
  const grd = ctx.createRadialGradient(CX, by, R*0.4, CX, by, glowR)
  grd.addColorStop(0,   hexAlpha(mood.glow, 0.42))
  grd.addColorStop(0.5, hexAlpha(mood.glow, 0.14))
  grd.addColorStop(1,   hexAlpha(mood.glow, 0))
  ctx.beginPath()
  ctx.ellipse(CX, by, glowR, glowR*0.92, 0, 0, Math.PI*2)
  ctx.fillStyle = grd; ctx.fill()

  // Body
  ctx.save()
  ctx.translate(CX, by)
  ctx.rotate(state.wobble)
  const bodyGrd = ctx.createRadialGradient(-R*0.28,-RY*0.32,R*0.08,0,0,R*1.1)
  bodyGrd.addColorStop(0,   lighten(mood.body, 0.38))
  bodyGrd.addColorStop(0.45, mood.body)
  bodyGrd.addColorStop(1,   darken(mood.body, 0.22))
  ctx.beginPath()
  ctx.ellipse(0, 0, R, RY, 0, 0, Math.PI*2)
  ctx.fillStyle = bodyGrd; ctx.fill()
  // Highlight
  const hlGrd = ctx.createRadialGradient(-R*0.26,-RY*0.30,0,-R*0.18,-RY*0.18,R*0.52)
  hlGrd.addColorStop(0,   'rgba(255,255,255,0.62)')
  hlGrd.addColorStop(0.5, 'rgba(255,255,255,0.10)')
  hlGrd.addColorStop(1,   'rgba(255,255,255,0)')
  ctx.beginPath()
  ctx.ellipse(0, 0, R, RY, 0, 0, Math.PI*2)
  ctx.fillStyle = hlGrd; ctx.fill()
  ctx.restore()

  drawFace(mood, R, RY, by, amp, t)

  // Talking rings
  if (state.animState === 'talking' && amp > 0.04) {
    for (let i=1; i<=3; i++) {
      ctx.beginPath()
      ctx.arc(CX, by, R + 8 + i*14*amp, 0, Math.PI*2)
      ctx.strokeStyle = hexAlpha(mood.glow, (0.45-i*0.1)*amp)
      ctx.lineWidth = 3 - i*0.5; ctx.stroke()
    }
  }

  // Thinking dots
  if (state.animState === 'thinking' || state.currentMood === 'thinking') {
    state.thinkDot += dt * 2.2
    for (let i=0; i<3; i++) {
      const pulse = Math.sin(state.thinkDot - i*0.9)
      ctx.beginPath()
      ctx.arc(CX + R + 12 + i*15, by - R*0.25, 4+pulse*2.5, 0, Math.PI*2)
      ctx.fillStyle = hexAlpha(mood.glow, 0.45+pulse*0.4); ctx.fill()
    }
  }

  // Listening ring
  if (state.animState === 'listening') {
    const pulse = (Math.sin(state.breathe*3)+1)*0.5
    ctx.beginPath()
    ctx.arc(CX, by, R + 7 + pulse*10, 0, Math.PI*2)
    ctx.strokeStyle = hexAlpha(mood.glow, 0.55*pulse+0.18)
    ctx.lineWidth = 2.5; ctx.stroke()
  }

  // Tears
  if (state.tearAmt > 0.1) {
    const tt = (t * 1.4) % 1
    const ty = by + R*0.15 + tt*R*0.6
    ctx.beginPath(); ctx.ellipse(CX-R*0.30, ty, 3, 5, 0, 0, Math.PI*2)
    ctx.fillStyle = hexAlpha('#88CCFF', state.tearAmt*(1-tt*0.5)*0.75); ctx.fill()
    const tt2 = ((t*1.4)+0.45)%1
    const ty2 = by + R*0.15 + tt2*R*0.6
    ctx.beginPath(); ctx.ellipse(CX+R*0.30, ty2, 3, 5, 0, 0, Math.PI*2)
    ctx.fillStyle = hexAlpha('#88CCFF', state.tearAmt*(1-tt2*0.5)*0.75); ctx.fill()
  }
}

// ── DRAW FACE ─────────────────────────────────────────────────────────────────
function drawFace(mood, R, RY, by, amp, t) {
  const blink = state.blinkVal
  const lx    = state.lookX * 7
  const ly    = state.lookY * 4
  const baseR = R * 0.27
  const EL    = { x: CX - R*0.30, y: by - R*0.10 }
  const ER    = { x: CX + R*0.30, y: by - R*0.10 }

  ;[EL, ER].forEach(({x, y}, idx) => {
    const eyeH = baseR * (1 - blink) * (1 + state.eyeWide*0.55) * (1 - state.eyeSquint*0.28)
    if (eyeH < 1) return

    const droopAngle = state.eyeDrop * (idx===0 ? 0.26 : -0.26)
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(droopAngle)

    // White
    ctx.beginPath()
    ctx.ellipse(0, 0, baseR, eyeH, 0, 0, Math.PI*2)
    ctx.fillStyle = 'rgba(255,255,255,0.93)'; ctx.fill()

    if (blink < 0.5) {
      const irisR = baseR * 0.60
      // Iris
      ctx.beginPath()
      ctx.ellipse(lx*0.4, ly*0.4, irisR, irisR*(1-state.eyeSquint*0.22), 0, 0, Math.PI*2)
      ctx.fillStyle = mood.iris; ctx.fill()
      // Pupil
      const dilate = 1 + (state.happiness-50)/150
      const pupilR = irisR * 0.50 * dilate
      ctx.beginPath()
      ctx.ellipse(lx, ly, pupilR, pupilR, 0, 0, Math.PI*2)
      ctx.fillStyle = mood.pupil; ctx.fill()
      // Shine x2
      ctx.beginPath(); ctx.ellipse(lx-irisR*0.26, ly-irisR*0.26, irisR*0.21, irisR*0.21, 0, 0, Math.PI*2)
      ctx.fillStyle = 'rgba(255,255,255,0.90)'; ctx.fill()
      ctx.beginPath(); ctx.ellipse(lx+irisR*0.18, ly-irisR*0.32, irisR*0.11, irisR*0.11, 0, 0, Math.PI*2)
      ctx.fillStyle = 'rgba(255,255,255,0.55)'; ctx.fill()

      // Happy squint crinkle — ^_^ lines under eye
      if (state.eyeSquint > 0.15 && blink < 0.3) {
        ctx.beginPath()
        ctx.moveTo(-baseR*0.48, baseR*0.58)
        ctx.quadraticCurveTo(0, baseR*0.95, baseR*0.48, baseR*0.58)
        ctx.strokeStyle = hexAlpha(mood.pupil, state.eyeSquint*0.50)
        ctx.lineWidth = 1.8; ctx.lineCap = 'round'; ctx.stroke()
      }
    }
    ctx.restore()

    // Eyebrows
    const browDir = idx === 0 ? -1 : 1
    const browY   = y - baseR*1.58 - state.eyeDrop*4
    ctx.save()
    ctx.translate(x, browY)
    ctx.rotate(state.browAngle * browDir)
    ctx.beginPath()
    ctx.moveTo(-baseR*0.52, 0)
    ctx.quadraticCurveTo(0, state.browAngle*browDir*-9, baseR*0.52, 0)
    ctx.strokeStyle = hexAlpha(mood.pupil, 0.68)
    ctx.lineWidth = 2.8; ctx.lineCap = 'round'; ctx.stroke()
    ctx.restore()
  })

  // ── MOUTH ─────────────────────────────────────────────────────────────
  const mx = CX
  const my = by + R*0.38
  const crv = state.mouthCurve

  // Talking mouth overrides
  if (state.animState === 'talking' && amp > 0.04) {
    const ow = R*(0.22 + amp*0.12)
    const oh = R*(0.05 + amp*0.19)
    ctx.beginPath(); ctx.ellipse(mx, my+oh*0.3, ow, oh+2, 0, 0, Math.PI*2)
    ctx.fillStyle = hexAlpha(mood.pupil, 0.62); ctx.fill()
    ctx.beginPath(); ctx.ellipse(mx, my+oh*0.45, ow*0.65, oh*0.58, 0, 0, Math.PI*2)
    ctx.fillStyle = 'rgba(255,155,155,0.42)'; ctx.fill()
    return
  }

  if (Math.abs(crv) < 0.05) {
    // Flat
    ctx.beginPath(); ctx.moveTo(mx-R*0.20, my); ctx.lineTo(mx+R*0.20, my)
    ctx.strokeStyle = hexAlpha(mood.pupil, 0.45)
    ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.stroke()
  } else if (crv > 0) {
    // Smile
    const depth = R*0.10*crv
    const width = R*(0.22 + crv*0.10)
    ctx.beginPath(); ctx.moveTo(mx-width, my); ctx.quadraticCurveTo(mx, my+depth, mx+width, my)
    ctx.strokeStyle = hexAlpha(mood.pupil, 0.68)
    ctx.lineWidth = 2.8; ctx.lineCap = 'round'; ctx.stroke()
    // Teeth hint for big grin
    if (crv > 1.5) {
      ctx.beginPath(); ctx.ellipse(mx, my+depth*0.45, width*0.72, depth*0.52, 0, 0, Math.PI)
      ctx.fillStyle = 'rgba(255,255,255,0.52)'; ctx.fill()
    }
    // Blush
    if (state.blushAmt > 0.05) {
      ;[-1,1].forEach(dir => {
        const bx = CX + dir*R*0.53
        const brd = ctx.createRadialGradient(bx,my-R*0.04,0,bx,my-R*0.04,R*0.27)
        brd.addColorStop(0, `rgba(255,138,138,${state.blushAmt*0.32})`)
        brd.addColorStop(1, 'rgba(255,138,138,0)')
        ctx.beginPath(); ctx.ellipse(bx, my-R*0.04, R*0.27, R*0.17, 0, 0, Math.PI*2)
        ctx.fillStyle = brd; ctx.fill()
      })
    }
  } else {
    // Frown
    const depth = R*0.10*Math.abs(crv)
    const width = R*(0.20 + Math.abs(crv)*0.08)
    ctx.beginPath(); ctx.moveTo(mx-width, my); ctx.quadraticCurveTo(mx, my-depth, mx+width, my)
    ctx.strokeStyle = hexAlpha(mood.pupil, 0.60)
    ctx.lineWidth = 2.8; ctx.lineCap = 'round'; ctx.stroke()
  }
}

// ── LOOP ──────────────────────────────────────────────────────────────────────
let lastTime = performance.now()

function loop(now) {
  requestAnimationFrame(loop)
  const dt = Math.min((now - lastTime)/1000, 0.05)
  lastTime  = now
  const t   = now / 1000

  state.amplitude += (state.targetAmp - state.amplitude) * 0.22

  // Blink
  state.blinkT += dt
  if (state.blinkT >= state.nextBlink) {
    state.blinkT = 0; state.nextBlink = 2.5 + Math.random()*4
    triggerBlink()
  }

  // Eye wander
  state.nextLook -= dt
  if (state.nextLook <= 0) {
    state.nextLook    = 1.5 + Math.random()*3.0
    state.targetLookX = (Math.random()-0.5)*1.5
    state.targetLookY = (Math.random()-0.5)*0.9
  }
  state.lookX += (state.targetLookX - state.lookX) * dt * 4.5
  state.lookY += (state.targetLookY - state.lookY) * dt * 4.5

  // Mood
  setMood(computeMood())
  updateMoodTransition(dt)
  updateReaction(dt)
  if (!state.reactionType) updateMoodBody(t)

  // animState eye overrides
  if (state.animState === 'listening') { state.targetLookX=0; state.targetLookY=-0.4 }
  if (state.animState === 'thinking')  { state.targetLookX=-0.7; state.targetLookY=-0.6 }

  // talking animState body
  if (state.animState === 'talking' && !state.reactionType) {
    state.squishX = 1 + state.amplitude*0.08
    state.squishY = 1 - state.amplitude*0.06
    state.wobble  = Math.sin(t*5)*state.amplitude*0.05
    state.bounce  = Math.sin(t*7)*state.amplitude*4
  }

  draw(dt)
}

// ── BLINK ─────────────────────────────────────────────────────────────────────
function triggerBlink() {
  const dur = 110, start = performance.now()
  function ab(now) {
    const p = (now-start)/dur
    if (p < 0.5)      { state.blinkVal = p*2;       requestAnimationFrame(ab) }
    else if (p < 1.0) { state.blinkVal = (1-p)*2;   requestAnimationFrame(ab) }
    else               { state.blinkVal = 0 }
  }
  requestAnimationFrame(ab)
}

// ── WEBSOCKET ─────────────────────────────────────────────────────────────────
function connectWS() {
  const ws = new WebSocket('ws://localhost:8000/ws/avatar')
  ws.onopen = () => console.log('WS connected')
  ws.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data)

      if (d.type === 'heartbeat' && d.emotion) {
        const prevHappy  = state.happiness
        const prevEnergy = state.energy
        state.happiness  = d.emotion.happiness
        state.trust      = d.emotion.trust
        state.energy     = d.emotion.energy
        state.attachment = d.emotion.attachment

        const dH = state.happiness - prevHappy
        const dE = state.energy    - prevEnergy

        if      (dH > 12)  triggerReaction(state.happiness > 75 ? 'excited_bounce' : 'happy_jump')
        else if (dH < -8)  triggerReaction('sad_droop')
        else if (dE > 15)  triggerReaction('surprise_pop')

        if (d.animation === 'surprised') triggerReaction('surprise_pop')
        if (d.animation === 'thinking')  triggerReaction('thinking_tilt')
      }

      if (d.amplitude !== undefined) state.targetAmp = d.amplitude
      if (d.animation)  state.animState = d.animation
      if (d.type === 'idle') state.animState = 'idle'

    } catch(_) {}
  }
  ws.onclose = () => setTimeout(connectWS, 3000)
  ws.onerror = () => {}
}
connectWS()

// ── DRAG ──────────────────────────────────────────────────────────────────────
let dragging=false, dragStartX, dragStartY
canvas.addEventListener('mousedown', e => {
  dragging=true; dragStartX=e.screenX; dragStartY=e.screenY
  document.body.classList.add('dragging')
})
window.addEventListener('mousemove', e => {
  if (!dragging) return
  const dx=e.screenX-dragStartX, dy=e.screenY-dragStartY
  dragStartX=e.screenX; dragStartY=e.screenY
  windowControls.moveWindowDelta(dx, dy)
})
window.addEventListener('mouseup', () => {
  dragging=false; document.body.classList.remove('dragging')
})

// ── HELPERS ───────────────────────────────────────────────────────────────────
function hexAlpha(hex, a) {
  return `rgba(${parseInt(hex.slice(1,3),16)},${parseInt(hex.slice(3,5),16)},${parseInt(hex.slice(5,7),16)},${a})`
}
function lighten(hex, amt) {
  return `rgb(${Math.round(Math.min(255,parseInt(hex.slice(1,3),16)+255*amt))},${Math.round(Math.min(255,parseInt(hex.slice(3,5),16)+255*amt))},${Math.round(Math.min(255,parseInt(hex.slice(5,7),16)+255*amt))})`
}
function darken(hex, amt) {
  return `rgb(${Math.round(Math.max(0,parseInt(hex.slice(1,3),16)-255*amt))},${Math.round(Math.max(0,parseInt(hex.slice(3,5),16)-255*amt))},${Math.round(Math.max(0,parseInt(hex.slice(5,7),16)-255*amt))})`
}

requestAnimationFrame(loop)