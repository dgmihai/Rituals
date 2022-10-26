// Populate rituals
let RITUALS_FILE = "rituals.json";
let RITUALS_DATA_FILE = "rituals_data.json";

let rituals = require("Storage").readJSON(RITUALS_FILE, true);

function writeData() {
  require("Storage").writeJSON(RITUALS_DATA_FILE, rituals);
  print(rituals);
}

var m = {
  "": {
    "title": "Rituals",
  }
};

var settings = require('Storage').readJSON("messages.settings.json", true) || {};

// FONTS
var fontSmall = "6x8";
var fontMedium = g.getFonts().includes("6x15")?"6x15":"6x8:2";
var fontBig = g.getFonts().includes("12x20")?"12x20":"6x8:2";
var fontLarge = g.getFonts().includes("6x15")?"6x15:2":"6x8:4";
var fontHuge = g.getFonts().includes("12x20")?"12x20:2":"6x8:5";

// hack for 2v10 firmware's lack of ':size' font handling
try {
  g.setFont("6x8:2");
} catch (e) {
  g._setFont = g.setFont;
  g.setFont = function(f,s) {
    if (f.includes(":")) {
      f = f.split(":");
      return g._setFont(f[0],f[1]);
    }
    return g._setFont(f,s);
  };
}

// TIMER
var counter, counterInterval, expired, pause;

function getTime(add) {
  let t = new Date();
  t.setSeconds(t.getSeconds() + add);
  min = t.getMinutes();
  if (min < 10) min = "0" + min;
  let suffix = t.getHours() < 12 ? " am" : " pm";
  let hour = t.getHours() == 0 ? "12" : t.getHours();
  return t.getHours() + ":" + min + suffix;
}

function timeFormatted(sec) {
  sec = Math.abs(sec);
  var ret = "";
  var min = Math.floor(sec / 60);
  sec = sec % 60;
  var hour = Math.floor(min / 60);
  min = min % 60;
  if (sec < 10) {
    sec = "0" + sec;
  }
  if (hour > 0) {
    if (min < 10) {
      min = "0" + min;
    }
    ret = hour + ":";
  }
  return ret + min + ":" + sec;
}

function tick() {
  if (pause) {
    if (rituals[id].acts[idx].time.started) {
      rituals[id].acts[idx].time.paused++;
      rituals[id].time.paused++;
    }
  } else {
    if (!rituals[id].acts[idx].time.started) {
      rituals[id].acts[idx].time.started = Math.floor(Date.now() / 1000);
      rituals[id].acts[idx].status = "active";
    }
    rituals[id].acts[idx].time.actual++;
    rituals[id].time.actual++;
    if (expired) {
      counter = rituals[id].acts[idx].time.expected - rituals[id].acts[idx].time.actual;
    } else {
      counter = rituals[id].acts[idx].time.actual - rituals[id].acts[idx].time.expected;
      if (counter == 0 && rituals[id].acts[idx].time.expected != 0) {
        Bangle.buzz();
        expired = true;
      }
    }
  }
  redraw();
}

// GRAPHICS
var layout, btn, upperText, titleText, titleFont, counterText, etaText;
var btnPause = {type:"btn", src:atob("EhKCAP/wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP///wAP/w=="), cb: l=>{
  pause = true;
  rituals[id].acts[idx].status = "incomplete";
  redraw();
}};
var btnPlay = {type:"btn", src:atob("EhKCAPAAAAAP8AAAAP/wAAAP//AAAP//8AAP///wAP////AP////8P////////////////8P////AP///wAP//8AAP//AAAP/wAAAP8AAAAPAAAAAA=="), cb: l=>{
  pause = false;
  rituals[id].acts[idx].status = "active";
  redraw();
}};

function redraw() {
  let fg, bg, counterFg, etaFg;
  btn = pause ? btnPlay : btnPause;
  if (layout != undefined)
    layout.clear();
  // Colors
  etaFg = '#222222';
  if (pause && rituals[id].acts[idx].time.started) {
    bg = '#FFF5BC';
    fg = g.theme.fg2;
    counterFg = g.theme.fg2;
  } else {
    bg = g.theme.bg2;
    fg = g.theme.fg2;
    counterFg = g.theme.fg2;
  }
  if (expired) {
    bg =  '#FFCCCC';
    counterFg = '#F00000';
  }
  if (rituals[id].acts[idx].time.expected == 0) {
    counterFg = '#222222';
    etaText = timeFormatted(counter);
    counterText = getTime(0);
  } else {
    counterText = timeFormatted(counter);
    etaText = getTime(rituals[id].time.expected - rituals[id].time.actual);
  }

  // Layout
  var Layout = require("Layout");
  layout = new Layout( {
    type:"v", c: [
    {type:"h", fillx:1, c: [
      {type:"v", fillx:1, c: [
        {type:"txt", id:"upper", font:fontSmall, label:upperText, bgCol:bg, col: fg, fillx:1, pad:2, halign:1 },
        {type:"txt", id:"title", font:titleFont, height:"44", label:titleText, bgCol:bg, col: fg, fillx:1, pad:2 },
      ]},
    ]},
    {type:"txt", id:"counter", font:fontHuge, label:counterText, col:counterFg, fillx:1, filly:1, pad:2},
    {type:"txt", id:"eta", font:fontBig, label:etaText, col:etaFg, fillx:1, filly:1, pad:2},
    {type:"h", id:"buttons", fillx:1, c: [ btn ] }
  ]}, {lazy:true});
  layout.render();
}

// Show
var idx, id, t_remaining;
function showRitual(x) {
  let start = Math.floor(Date.now() / 1000);
  rituals[x + start] = rituals[x];
  id = x + start;
  ritual[id].time.started = start;
  idx = 0;
  E.showMenu();
  g.clear();
  E.showMessage("Loading...");
  rituals[id].acts = expandRituals(id);
  for (let x in rituals[id].acts) {
    if (rituals[id].acts[x].duration) {
      rituals[id].time.expected = rituals[id].acts[x].time.expected + rituals[id].time.expected;
    }
  }
  showAct();
  rituals[id].acts[idx].time.started = Math.floor(Date.now() / 1000);
  tick();
  if (!counterInterval)
    counterInterval = setInterval(tick, 1000);
}

function showAct() {
  pause = false;
  if (rituals[id].acts.length > idx) {
    rituals[id].status = "active";
    upperText = rituals[id].name;
    titleText = rituals[id].acts[idx].name;
    duration = rituals[id].acts[idx].duration;
    elapsed = rituals[id].acts[idx].elapsed;
    elapsedPause = rituals[id].acts[idx].elapsedPause;
    if (!rituals[id].acts[idx].time) rituals[id].acts[idx].time = { actual:0, expected:0, paused:0 };
    else {
      if (!rituals[id].acts[idx].time.actual) rituals[id].acts[idx].time.actual = 0;
      if (!rituals[id].acts[idx].time.expected) rituals[id].acts[idx].time.expected = 0;
      if (!rituals[id].acts[idx].time.paused) rituals[id].acts[idx].time.paused = 0;
    }
    let diff = rituals[id].acts[idx].time.actual - rituals[id].acts[idx].time.expected;
    expired = (rituals[id].acts[idx].time.expected != 0 && diff > 0) ? true : false;
    counter = expired ? diff : rituals[id].acts[idx].time.expected - rituals[id].acts[idx].time.actual;
    // Set font sizes
    let w = g.getWidth(), lines;
    titleFont = fontHuge;
    if (g.setFont(titleFont).stringWidth(titleText) > w) {
      titleFont = fontBig;
      if (settings.fontSize!=1 && g.setFont(titleFont).stringWidth(titleText) > w*2) {
        titleFont = fontMedium;
      }
    }
    if (g.setFont(titleFont).stringWidth(titleText) > w) {
      lines = g.wrapString(titleText, w);
      titleText = (lines.length>2) ? lines.slice(0,2).join("\n")+"..." : lines.join("\n");
    }
    redraw();
  } else {
    clearInterval();
    counterInterval = undefined;
    g.clear();
    E.showMessage("COMPLETE! :)");
    writeData();
  }
}

/* Navigate by swiping
    swipe up: skip
    swipe down: show description
    swipe right: previous event
    swipe left: next event */
var drag = 0;
Bangle.on("drag", e => {
  if (!drag) { // start dragging
    drag = {x: e.x, y: e.y};
  } else if (!e.b) { // released
    const dx = e.x-drag.x, dy = e.y-drag.y;
    drag = null;
    if (Math.abs(dx)>Math.abs(dy)+10) {
      if (dx>0) {
        // right
        if (idx>0) {
          rituals[id].acts[idx].status = "incomplete";
          idx--;
          showAct();
        }
        print("Right")
      } else {
        // left
        rituals[id].acts[idx].status = "completed";
        idx++;
        showAct();
        print("Left")
      }
    } else if (Math.abs(dy)>Math.abs(dx)+10) {
      if (dy>0) {
        // down
        print("Down")
      } else {
        // up
        rituals[id].acts[idx].status = "skipped";
        rituals[id].acts.push(rituals[id].acts[idx]);
        rituals[id].acts.splice(idx, 1);
        showAct();
        print("Up")
      }
    }
  }
});

function expandRituals(rid) {
  let ret = [];
  for (let x in rituals[rid].acts) {
    if (!rituals[rid].acts[x].ritual) ret.push(rituals[rid].acts[x]);
    if (rituals[rid].acts[x].next) ret = ret.concat(expandRituals(rituals[rid].acts[x].next));
  }
  return ret;
}

for (var id in rituals) {
  const rid = id;
  rituals[id].time = { expected: 0 };
  m[rituals[rid].name] = () => {
    showRitual(String(rid));
  };
}

E.showMenu(m);
setWatch( ()=>{
  clearInterval();
  counterInterval = undefined;
  writeData();
  g.clear();
  E.showMenu(m);
}, BTN1, {repeat: true});