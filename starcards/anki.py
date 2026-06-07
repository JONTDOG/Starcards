from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .models import CardDraft


@dataclass(slots=True)
class AnkiSettings:
    connect_url: str = "http://localhost:8765"
    root_deck: str = "StarCards"
    include_sched: bool = False


MCQ_FRONT_TEMPLATE = """
<div class="mcq-wrap">
  <div class="sc-question">{{Question}}</div>
  <div class="sc-extra">{{WhyThisMatters}}</div>
  <div class="mcq-options">
    <label class="mcq-option"><input type="radio" name="mcq"> <span>{{Q_1}}</span></label>
    <label class="mcq-option"><input type="radio" name="mcq"> <span>{{Q_2}}</span></label>
    <label class="mcq-option"><input type="radio" name="mcq"> <span>{{Q_3}}</span></label>
    <label class="mcq-option"><input type="radio" name="mcq"> <span>{{Q_4}}</span></label>
  </div>
  <button class="mcq-check" onclick="checkMcq()">Check Answer</button>
  <div id="mcq-feedback" class="mcq-feedback" style="display:none;"></div>
</div>
<script>
(function() {
  var correctIndex = 0;
  window.checkMcq = function() {
    var options = document.querySelectorAll('.mcq-option input');
    var feedback = document.getElementById('mcq-feedback');
    var chosen = -1;
    for (var i = 0; i < options.length; i++) {
      if (options[i].checked) {
        chosen = i;
        break;
      }
    }
    if (chosen < 0) {
      feedback.style.display = 'block';
      feedback.textContent = 'Choose an answer first.';
      return;
    }
    var chosenText = document.querySelectorAll('.mcq-option span')[chosen].textContent;
    var correctText = document.querySelectorAll('.mcq-option span')[correctIndex].textContent;
    var ok = chosen === correctIndex;
    feedback.className = 'mcq-feedback ' + (ok ? 'mcq-correct' : 'mcq-wrong');
    feedback.textContent = ok ? 'Correct.' : 'Incorrect. Correct answer: ' + correctText;
    feedback.style.display = 'block';
    for (var j = 0; j < options.length; j++) {
      options[j].disabled = true;
    }
    var btn = document.querySelector('.mcq-check');
    if (btn) btn.style.display = 'none';
  };
})();
</script>
<style>
.mcq-wrap { font-family: Arial, sans-serif; }
.sc-question { font-size: 1.25em; font-weight: bold; margin-bottom: 10px; color: #fff; }
.sc-extra { margin-bottom: 14px; color: #8ec5ff; font-size: 0.95em; }
.mcq-options { display: flex; flex-direction: column; gap: 10px; margin: 10px 0 14px; }
.mcq-option { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border: 1px solid #444; border-radius: 6px; background: #1f1f1f; color: #fff; cursor: pointer; }
.mcq-option input { margin-top: 4px; }
.mcq-check { padding: 10px 14px; border: none; border-radius: 6px; background: #4a90d9; color: #fff; cursor: pointer; font-weight: bold; }
.mcq-feedback { margin-top: 12px; padding: 10px 12px; border-radius: 6px; font-weight: bold; }
.mcq-correct { background: #1a4731; color: #9ae6b4; }
.mcq-wrong { background: #4a1010; color: #feb2b2; }
</style>
"""

MCQ_BACK_TEMPLATE = """
{{FrontSide}}
<hr>
<div class="sc-answer"><strong>Answer:</strong> {{Q_1}}</div>
<div class="sc-meta">{{Sources}}</div>
<style>
.sc-answer { color: #fff; font-size: 1.1em; margin-bottom: 8px; }
.sc-meta { color: #8ec5ff; font-size: 0.95em; }
</style>
"""

ESSAY_FRONT_TEMPLATE = """
<div class="essay-shell">
  <div class="essay-question">{{Question}}</div>
  <div class="essay-scope">{{Scope}}</div>
  <div class="essay-prompt">Write your answer below, then check it against the model answer.</div>
  <textarea id="userAnswer" class="essay-input" placeholder="Type your answer here..." rows="8"></textarea>
  <button class="essay-button" onclick="checkAnswer()">Check My Answer</button>
  <div id="feedback" style="display:none;"></div>
</div>
<script>
(function() {
  var model = "{{ModelAnswer}}";
  var keyTerms = "{{KeyTerms}}".split("|").map(function(t) { return t.trim(); }).filter(function(t) { return t.length > 0; });
  var feedbackEl = document.getElementById("feedback");
  var inputEl = document.getElementById("userAnswer");

  function normalize(text) {
    return (text || "")
      .toLowerCase()
      .replace(/[^\\w\\s]/g, " ")
      .replace(/\\s+/g, " ")
      .trim();
  }

  function renderFeedback(passed, message) {
    feedbackEl.style.display = "block";
    feedbackEl.innerHTML = "";
    var summary = document.createElement("div");
    summary.style.padding = "12px";
    summary.style.borderRadius = "10px";
    summary.style.marginTop = "12px";
    summary.style.background = passed ? "#1a4731" : "#4a1010";
    summary.style.color = passed ? "#9ae6b4" : "#feb2b2";
    summary.style.fontWeight = "bold";
    summary.textContent = message;
    feedbackEl.appendChild(summary);

    var compare = document.createElement("div");
    compare.style.marginTop = "10px";
    compare.style.padding = "12px";
    compare.style.borderRadius = "10px";
    compare.style.background = "#0d2a45";
    compare.style.color = "#e8f0fe";
    compare.style.lineHeight = "1.5";
    compare.textContent = "Model answer: " + model;
    feedbackEl.appendChild(compare);
  }

  window.checkAnswer = function() {
    var actual = normalize(inputEl.value);
    var expected = normalize(model);
    var passed = actual.length > 0 && expected.length > 0 && actual === expected;
    if (!passed && actual.length > 0 && keyTerms.length > 0) {
      var hits = 0;
      keyTerms.forEach(function(term) {
        if (actual.indexOf(normalize(term)) !== -1) {
          hits++;
        }
      });
      passed = hits >= Math.max(1, Math.ceil(keyTerms.length / 2));
    }
    renderFeedback(
      passed ? "✓ Your answer matches the expected response or covers the main key terms." : "✗ Your answer does not yet match the model answer closely enough.",
      passed
    );
  };
})();
</script>
"""

ESSAY_BACK_TEMPLATE = """
{{FrontSide}}
<hr>
<div class="model-answer-header">Model Answer:</div>
<div class="model-answer">{{ModelAnswer}}</div>
"""

MATCHING_FRONT_TEMPLATE = """
<div id="match-root"></div>
<div id="match-data" style="display:none;">{{Pairs}}</div>
<script>
(function() {
  var raw = document.getElementById("match-data").textContent.trim();
  var fields = raw.split("|").map(function(s){ return s.trim(); }).filter(function(s){ return s.length > 0; });
  var half = Math.floor(fields.length / 2);
  var pairs = [];
  for (var i = 0; i < half; i++) {
    pairs.push({ term: fields[i], def: fields[i + half] });
  }

  var defs = pairs.map(function(p) { return { text: p.def, matched: false }; });
  for (var j = defs.length - 1; j > 0; j--) {
    var k = Math.floor(Math.random() * (j + 1));
    var tmp = defs[j]; defs[j] = defs[k]; defs[k] = tmp;
  }

  var selected = null;
  var slots = new Array(pairs.length).fill(null);
  var root = document.getElementById("match-root");

  function css(el, styles) {
    Object.keys(styles).forEach(function(key) { el.style[key] = styles[key]; });
  }

  function render() {
    root.innerHTML = "";

    var title = document.createElement("div");
    css(title, {fontFamily:"Arial,sans-serif",fontWeight:"bold",fontSize:"15px",marginBottom:"10px",color:"#fff"});
    title.textContent = "Click a definition, then click the matching term slot:";
    root.appendChild(title);

    var grid = document.createElement("div");
    css(grid, {display:"flex",gap:"16px",alignItems:"flex-start"});

    var left = document.createElement("div");
    css(left, {flex:"1",display:"flex",flexDirection:"column",gap:"8px"});
    pairs.forEach(function(p, idx) {
      var slot = document.createElement("div");
      css(slot, {
        padding:"10px 12px",
        borderRadius:"6px",
        cursor:"pointer",
        border: slots[idx] !== null ? "2px solid #4a90d9" : "2px solid #444",
        background: slots[idx] !== null ? "#0d2a45" : "#222",
        minHeight:"56px"
      });
      var term = document.createElement("div");
      css(term, {fontWeight:"bold",color:"#fff",fontSize:"15px",marginBottom:"4px"});
      term.textContent = p.term;
      slot.appendChild(term);

      var slotContent = document.createElement("div");
      if (slots[idx] !== null) {
        css(slotContent, {color:"#7ec8f7",fontSize:"13px",lineHeight:"1.4"});
        slotContent.textContent = slots[idx];
      } else {
        css(slotContent, {color:"#666",fontSize:"12px",fontStyle:"italic"});
        slotContent.textContent = "— empty —";
      }
      slot.appendChild(slotContent);

      slot.addEventListener("click", function() { clickSlot(idx); });
      left.appendChild(slot);
    });

    var right = document.createElement("div");
    css(right, {flex:"1",display:"flex",flexDirection:"column",gap:"8px"});
    defs.forEach(function(d, idx) {
      if (d.matched) return;
      var def = document.createElement("div");
      css(def, {
        padding:"10px 12px",
        borderRadius:"6px",
        cursor:"pointer",
        background: selected === idx ? "#1a3f7a" : "#162030",
        border: selected === idx ? "2px solid #90cdf4" : "2px solid #2d4a7a",
        color:"#e8f0fe",
        fontSize:"13px",
        lineHeight:"1.5"
      });
      def.textContent = d.text;
      def.addEventListener("click", function() { clickDef(idx); });
      right.appendChild(def);
    });

    grid.appendChild(left);
    grid.appendChild(right);
    root.appendChild(grid);

    if (slots.every(function(s) { return s !== null; })) {
      var check = document.createElement("button");
      css(check, {
        marginTop:"14px",
        padding:"9px 20px",
        background:"#4a90d9",
        color:"#fff",
        border:"none",
        borderRadius:"6px",
        cursor:"pointer",
        fontSize:"15px",
        fontWeight:"bold"
      });
      check.textContent = "Check Matches";
      check.addEventListener("click", checkMatches);
      root.appendChild(check);
    }

    var feedback = document.createElement("div");
    feedback.id = "match-feedback";
    feedback.style.marginTop = "12px";
    root.appendChild(feedback);
  }

  function clickDef(i) {
    selected = (selected === i) ? null : i;
    render();
  }

  function clickSlot(i) {
    if (selected === null) {
      if (slots[i] !== null) {
        defs.forEach(function(d) { if (d.text === slots[i]) d.matched = false; });
        slots[i] = null;
        render();
      }
      return;
    }
    if (slots[i] !== null) {
      defs.forEach(function(d) { if (d.text === slots[i]) d.matched = false; });
    }
    slots[i] = defs[selected].text;
    defs[selected].matched = true;
    selected = null;
    render();
  }

  function checkMatches() {
    var fb = document.getElementById("match-feedback");
    fb.innerHTML = "";
    var correct = 0;
    pairs.forEach(function(p, idx) {
      var row = document.createElement("div");
      if (slots[idx] === p.def) {
        correct++;
        css(row, {background:"#1a4731",color:"#9ae6b4",padding:"6px 10px",margin:"3px 0",borderRadius:"4px",fontSize:"14px"});
        row.textContent = "✓ " + p.term;
      } else {
        css(row, {background:"#4a1010",color:"#feb2b2",padding:"6px 10px",margin:"3px 0",borderRadius:"4px",fontSize:"14px"});
        row.textContent = "✗ " + p.term + " → " + p.def;
      }
      fb.appendChild(row);
    });
    var score = document.createElement("div");
    css(score, {fontWeight:"bold",marginTop:"10px",padding:"9px",background:"#111",color:"#fff",borderRadius:"4px",fontSize:"15px"});
    score.textContent = "Score: " + correct + "/" + pairs.length;
    fb.appendChild(score);
  }

  render();
})();
</script>
<style>
.card { font-family: Arial, sans-serif; }
</style>
"""

MATCHING_BACK_TEMPLATE = """
{{FrontSide}}
<hr>
<div style="font-family:Arial,sans-serif;color:#fff;">
  <div style="font-weight:bold;margin-bottom:8px;">Correct matches</div>
  <div>{{Pairs}}</div>
</div>
"""

TRUEFALSE_FRONT_TEMPLATE = """
<div class="tf-shell">
  <div class="tf-label">TRUE OR FALSE?</div>
  <div class="tf-statement">{{Statement}}</div>
  <div class="tf-buttons">
    <button onclick="showResult('True')">TRUE</button>
    <button onclick="showResult('False')">FALSE</button>
  </div>
  <div id="tf-feedback" style="display:none;"></div>
</div>
<script>
(function() {
  var answer = "{{Answer}}".trim();
  var correction = "{{Correction}}";
  var buttons = document.querySelectorAll(".tf-buttons button");
  window.showResult = function(choice) {
    var feedback = document.getElementById("tf-feedback");
    var correct = choice === answer;
    feedback.style.display = "block";
    feedback.innerHTML = "";

    var res = document.createElement("div");
    res.style.padding = "12px";
    res.style.borderRadius = "10px";
    res.style.marginBottom = "8px";
    res.style.fontFamily = "Arial,sans-serif";
    res.style.fontSize = "15px";
    res.style.fontWeight = "bold";
    res.style.background = correct ? "#1a4731" : "#4a1010";
    res.style.color = correct ? "#9ae6b4" : "#feb2b2";
    res.textContent = correct ? "✓ Correct." : "✗ Incorrect. The correct answer is " + answer + ".";
    feedback.appendChild(res);

    var corr = document.createElement("div");
    corr.style.padding = "12px";
    corr.style.borderRadius = "10px";
    corr.style.background = "#0d2a45";
    corr.style.color = "#e8f0fe";
    corr.style.fontFamily = "Arial,sans-serif";
    corr.style.fontSize = "14px";
    corr.style.lineHeight = "1.5";
    corr.style.borderLeft = "3px solid #4a90d9";
    corr.textContent = correction;
    feedback.appendChild(corr);

    for (var i = 0; i < buttons.length; i++) {
      buttons[i].disabled = true;
      buttons[i].style.opacity = "0.6";
      buttons[i].style.cursor = "default";
    }
  };
})();
</script>
"""

TRUEFALSE_BACK_TEMPLATE = """
<div class="tf-back-shell">
  <div class="tf-back-label">Answer</div>
  <div class="tf-back-answer">{{Answer}}</div>
  <div class="tf-back-label">Why</div>
  <div class="tf-back-correction">{{Correction}}</div>
</div>
"""

SCAFFOLD_FRONT_TEMPLATE = """
<div class="scaffold-shell">
  <div class="scaffold-head">
    <div class="scaffold-seq">{{Sequence}}</div>
    <div class="scaffold-step">Step {{Position}} of {{Total}}</div>
    <div class="scaffold-type">{{CardType}}</div>
  </div>
  <div class="scaffold-question">{{Question}}</div>
  <div class="scaffold-prompt">Type your answer below, then check it against the model answer.</div>
  <textarea id="scaffold-user-answer" class="scaffold-input" placeholder="Write your answer here..."></textarea>
  <div class="scaffold-controls">
    <button onclick="showHint()">Show Hint</button>
    <button onclick="checkAnswer()">Check My Answer</button>
    <button onclick="showAnswer()">Show Model Answer</button>
  </div>
  <div class="scaffold-nav">
    <button id="scaffold-prev-btn" onclick="showPrevStep()">Previous Step</button>
    <button id="scaffold-next-btn" onclick="showNextStep()">Next Step</button>
  </div>
  <div class="scaffold-hint" id="scaffold-hint">Hint hidden.</div>
  <div id="scaffold-answer" style="display:none;">{{ModelAnswer}}</div>
  <div id="scaffold-keyterms" style="display:none;">{{KeyTerms}}</div>
  <div id="scaffold-causalverb" style="display:none;">{{CausalVerb}}</div>
  <div id="scaffold-prev-question" style="display:none;">{{PrevQuestion}}</div>
  <div id="scaffold-prev-answer" style="display:none;">{{PrevAnswer}}</div>
  <div id="scaffold-next-question" style="display:none;">{{NextQuestion}}</div>
  <div id="scaffold-next-answer" style="display:none;">{{NextAnswer}}</div>
  <div id="scaffold-feedback" style="display:none;"></div>
  <div id="scaffold-step-context" style="display:none;"></div>
</div>
<script>
(function() {
  var hintEl = document.getElementById("scaffold-hint");
  var answerEl = document.getElementById("scaffold-answer");
  var feedbackEl = document.getElementById("scaffold-feedback");
  var inputEl = document.getElementById("scaffold-user-answer");
  var contextEl = document.getElementById("scaffold-step-context");
  var keyTerms = document.getElementById("scaffold-keyterms").textContent.split("|").map(function(t){ return t.trim(); }).filter(function(t){ return t.length > 0; });
  var causalVerb = document.getElementById("scaffold-causalverb").textContent.trim();
  var prevQuestion = document.getElementById("scaffold-prev-question").textContent.trim();
  var prevAnswer = document.getElementById("scaffold-prev-answer").textContent.trim();
  var nextQuestion = document.getElementById("scaffold-next-question").textContent.trim();
  var nextAnswer = document.getElementById("scaffold-next-answer").textContent.trim();
  var prevBtn = document.getElementById("scaffold-prev-btn");
  var nextBtn = document.getElementById("scaffold-next-btn");
  var cardType = "{{CardType}}".toLowerCase();
  var hints = [];
  if (cardType === "edge" && causalVerb) {
    hints = [causalVerb].concat(keyTerms);
  } else if (cardType === "hub" && causalVerb) {
    hints = causalVerb.split("|").map(function(t){ return t.trim(); }).filter(function(t){ return t.length > 0; }).concat(keyTerms);
  } else {
    hints = keyTerms.slice();
  }
  var hintIndex = 0;

  function normalize(text) {
    return (text || "")
      .toLowerCase()
      .replace(/[^\\w\\s]/g, " ")
      .replace(/\\s+/g, " ")
      .trim();
  }

  function renderFeedback(message, passed) {
    feedbackEl.style.display = "block";
    feedbackEl.innerHTML = "";
    var panel = document.createElement("div");
    panel.style.padding = "12px";
    panel.style.borderRadius = "10px";
    panel.style.marginTop = "12px";
    panel.style.fontFamily = "Arial,sans-serif";
    panel.style.fontSize = "14px";
    panel.style.lineHeight = "1.6";
    panel.style.background = passed ? "#1a4731" : "#4a1010";
    panel.style.color = passed ? "#9ae6b4" : "#feb2b2";
    panel.textContent = message;
    feedbackEl.appendChild(panel);

    var model = document.createElement("div");
    model.style.marginTop = "10px";
    model.style.padding = "12px";
    model.style.borderRadius = "10px";
    model.style.fontFamily = "Arial,sans-serif";
    model.style.fontSize = "14px";
    model.style.lineHeight = "1.6";
    model.style.background = "#0d2a45";
    model.style.color = "#e8f0fe";
    model.style.borderLeft = "3px solid #4a90d9";
    model.textContent = "Model answer: " + answerEl.textContent.trim();
    feedbackEl.appendChild(model);
  }

  function renderContext(title, question, answer) {
    contextEl.style.display = "block";
    contextEl.innerHTML = "";

    var panel = document.createElement("div");
    panel.style.marginTop = "12px";
    panel.style.padding = "12px";
    panel.style.borderRadius = "12px";
    panel.style.background = "#111827";
    panel.style.border = "1px solid #264c7a";
    panel.style.color = "#e8f0fe";
    panel.style.lineHeight = "1.55";

    var heading = document.createElement("div");
    heading.style.fontWeight = "700";
    heading.style.color = "#8ec5ff";
    heading.style.marginBottom = "6px";
    heading.textContent = title;
    panel.appendChild(heading);

    var q = document.createElement("div");
    q.style.marginBottom = "6px";
    q.textContent = question ? ("Question: " + question) : "No adjacent step available.";
    panel.appendChild(q);

    if (answer) {
      var a = document.createElement("div");
      a.textContent = "Model answer: " + answer;
      panel.appendChild(a);
    }

    contextEl.appendChild(panel);
  }

  function renderHint() {
    if (hints.length === 0) {
      hintEl.textContent = "No hints available.";
      return;
    }
    if (hintIndex <= 0) {
      hintEl.textContent = "Hint hidden.";
      return;
    }
    var visible = hints.slice(0, hintIndex);
    hintEl.textContent = "Hint: " + visible.join(" \u2192 ");
  }

  window.showHint = function() {
    hintIndex = Math.min(hints.length, hintIndex + 1);
    renderHint();
  };

  window.checkAnswer = function() {
    var expected = normalize(answerEl.textContent);
    var actual = normalize(inputEl.value);
    var passed = expected.length > 0 && actual.length > 0 && actual === expected;
    if (!passed && expected.length > 0 && actual.length > 0) {
      var matches = 0;
      var terms = keyTerms.length > 0 ? keyTerms : expected.split(" ").filter(function(t) { return t.length > 3; });
      terms.forEach(function(term) {
        if (actual.indexOf(normalize(term)) !== -1) {
          matches++;
        }
      });
      passed = matches > 0;
    }
    renderFeedback(
      passed ? "✓ Your response matches the model answer or includes the key terms." : "✗ Your response does not yet match the model answer closely enough.",
      passed
    );
  };

  window.showAnswer = function() {
    answerEl.style.display = "block";
    answerEl.scrollIntoView({behavior:"smooth", block:"nearest"});
  };

  window.showPrevStep = function() {
    if (!prevQuestion) {
      renderContext("Previous Step", "", "");
      return;
    }
    renderContext("Previous Step", prevQuestion, prevAnswer);
  };

  window.showNextStep = function() {
    if (!nextQuestion) {
      renderContext("Next Step", "", "");
      return;
    }
    renderContext("Next Step", nextQuestion, nextAnswer);
  };

  if (!prevQuestion) {
    prevBtn.disabled = true;
    prevBtn.style.opacity = "0.45";
    prevBtn.style.cursor = "default";
  }
  if (!nextQuestion) {
    nextBtn.disabled = true;
    nextBtn.style.opacity = "0.45";
    nextBtn.style.cursor = "default";
  }

  renderHint();
})();
</script>
"""

SCAFFOLD_BACK_TEMPLATE = """
<div class="scaffold-back-shell">
  <div class="scaffold-answer-head">Model Answer</div>
  <div class="scaffold-answer">{{ModelAnswer}}</div>
  <div class="scaffold-nav-hint">Use Show Hint to reveal the next clue in sequence.</div>
  <div class="scaffold-nav-hint">Use Previous Step and Next Step to preview neighboring steps.</div>
</div>
"""


class AnkiConnectClient:
    def __init__(self, settings: AnkiSettings):
        self.settings = settings

    def invoke(self, action: str, **params: Any) -> Any:
        response = requests.post(
            self.settings.connect_url,
            json={"action": action, "version": 6, "params": params},
            timeout=60,
        ).json()
        if response.get("error"):
            raise RuntimeError(f"AnkiConnect error ({action}): {response['error']}")
        return response.get("result")

    def create_deck(self, deck_name: str) -> None:
        self.invoke("createDeck", deck=deck_name)

    def model_names(self) -> list[str]:
        return self.invoke("modelNames") or []

    def ensure_models(self) -> None:
        models = set(self.model_names())
        if "StarCardsMCQInteractive" not in models:
            self.invoke(
                "createModel",
                modelName="StarCardsMCQInteractive",
                inOrderFields=[
                    "Question",
                    "Q_1",
                    "Q_2",
                    "Q_3",
                    "Q_4",
                    "Answers",
                    "QType",
                    "Sources",
                    "Extra1",
                    "Tags",
                    "WhyThisMatters",
                ],
                css=".card { font-family: Arial, sans-serif; font-size: 16px; max-width: 800px; margin: 0 auto; padding: 20px; }",
                cardTemplates=[{"Name": "MCQ", "Front": MCQ_FRONT_TEMPLATE, "Back": MCQ_BACK_TEMPLATE}],
            )
        if "StarCardsEssay" not in models:
            self.invoke(
                "createModel",
                modelName="StarCardsEssay",
                inOrderFields=["Question", "Scope", "ModelAnswer", "KeyTerms", "Source"],
                css="""
.card {
  font-family: Arial, sans-serif;
  font-size: 16px;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  color: #fff;
  background: #1f1f1f;
}
.essay-shell {
  border: 1px solid #3a3a3a;
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(18,24,39,0.95), rgba(24,24,24,0.95));
  box-shadow: 0 18px 48px rgba(0,0,0,0.28);
}
.essay-question {
  font-size: 1.18em;
  font-weight: 700;
  line-height: 1.45;
  margin-bottom: 10px;
}
.essay-scope, .essay-prompt {
  color: #8ec5ff;
  margin-bottom: 12px;
  line-height: 1.5;
}
.essay-input {
  width: 100%;
  min-height: 160px;
  resize: vertical;
  border-radius: 12px;
  border: 1px solid #4a4a4a;
  background: #141414;
  color: #fff;
  padding: 12px 14px;
  font-size: 15px;
  box-sizing: border-box;
}
.essay-button {
  margin-top: 12px;
  padding: 10px 18px;
  border: none;
  border-radius: 999px;
  background: #4a90d9;
  color: #fff;
  cursor: pointer;
  font-weight: 700;
}
.model-answer-header {
  color: #8ec5ff;
  font-weight: 700;
  margin-bottom: 8px;
}
.model-answer {
  line-height: 1.6;
}
""",
                cardTemplates=[{"Name": "Essay", "Front": ESSAY_FRONT_TEMPLATE, "Back": ESSAY_BACK_TEMPLATE}],
            )
        if "StarCardsMatchingInteractive" not in models:
            self.invoke(
                "createModel",
                modelName="StarCardsMatchingInteractive",
                inOrderFields=["Pairs", "Source"],
                css=".card { font-family: Arial, sans-serif; font-size: 16px; max-width: 800px; margin: 0 auto; padding: 20px; }",
                cardTemplates=[{"Name": "Matching", "Front": MATCHING_FRONT_TEMPLATE, "Back": MATCHING_BACK_TEMPLATE}],
            )
        if "StarCardsTrueFalseInteractive" not in models:
            self.invoke(
                "createModel",
                modelName="StarCardsTrueFalseInteractive",
                inOrderFields=["Statement", "Answer", "Correction", "Source"],
                css="""
.card {
  font-family: Arial, sans-serif;
  font-size: 16px;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  color: #fff;
  background: #1f1f1f;
}
.tf-shell, .tf-back-shell {
  border: 1px solid #3a3a3a;
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(18,24,39,0.95), rgba(24,24,24,0.95));
  box-shadow: 0 18px 48px rgba(0,0,0,0.28);
}
.tf-label, .tf-back-label {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #13233b;
  color: #8ec5ff;
  font-weight: bold;
  font-size: 13px;
  margin-bottom: 14px;
}
.tf-statement {
  font-size: 1.1em;
  font-weight: 700;
  line-height: 1.5;
  margin-bottom: 16px;
}
.tf-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.tf-buttons button {
  padding: 10px 18px;
  border: none;
  border-radius: 999px;
  background: #4a90d9;
  color: #fff;
  cursor: pointer;
  font-weight: 700;
}
.tf-back-answer, .tf-back-correction {
  line-height: 1.6;
  margin-bottom: 12px;
}
""",
                cardTemplates=[{"Name": "TrueFalse", "Front": TRUEFALSE_FRONT_TEMPLATE, "Back": TRUEFALSE_BACK_TEMPLATE}],
            )
        if "StarCardsScaffoldInteractive" not in models:
            self.invoke(
                "createModel",
                modelName="StarCardsScaffoldInteractive",
                inOrderFields=[
                    "Sequence",
                    "Position",
                    "Total",
                    "Question",
                    "ModelAnswer",
                    "KeyTerms",
                    "CardType",
                    "CausalVerb",
                    "Source",
                    "PrevQuestion",
                    "PrevAnswer",
                    "NextQuestion",
                    "NextAnswer",
                ],
                css="""
.card {
  font-family: Arial, sans-serif;
  font-size: 16px;
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  color: #fff;
  background: #1f1f1f;
}
.scaffold-shell, .scaffold-back-shell {
  border: 1px solid #3a3a3a;
  border-radius: 16px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(18,24,39,0.95), rgba(24,24,24,0.95));
  box-shadow: 0 18px 48px rgba(0,0,0,0.28);
}
.scaffold-head {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 14px;
}
.scaffold-seq, .scaffold-step, .scaffold-type, .scaffold-answer-head {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: #13233b;
  color: #8ec5ff;
  font-weight: bold;
  font-size: 13px;
}
.scaffold-question {
  font-size: 1.22em;
  font-weight: 700;
  color: #fff;
  margin: 6px 0 12px;
  line-height: 1.45;
}
.scaffold-prompt, .scaffold-nav-hint {
  color: #8ec5ff;
  font-size: 0.95em;
  margin-bottom: 10px;
}
.scaffold-input {
  width: 100%;
  min-height: 140px;
  resize: vertical;
  border-radius: 12px;
  border: 1px solid #4a4a4a;
  background: #141414;
  color: #fff;
  padding: 12px 14px;
  font-size: 15px;
  box-sizing: border-box;
  outline: none;
}
.scaffold-input:focus {
  border-color: #4a90d9;
  box-shadow: 0 0 0 2px rgba(74,144,217,0.2);
}
.scaffold-controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 12px 0;
}
.scaffold-nav {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 0 0 12px;
}
.scaffold-controls button {
  padding: 10px 14px;
  border: none;
  border-radius: 999px;
  background: #4a90d9;
  color: #fff;
  cursor: pointer;
  font-weight: 700;
}
.scaffold-nav button {
  padding: 9px 14px;
  border: 1px solid #4a90d9;
  border-radius: 999px;
  background: transparent;
  color: #8ec5ff;
  cursor: pointer;
  font-weight: 700;
}
.scaffold-hint {
  padding: 12px;
  border-radius: 12px;
  background: #0d2a45;
  color: #e8f0fe;
  border-left: 3px solid #4a90d9;
  line-height: 1.55;
}
.scaffold-answer {
  margin-top: 12px;
  padding: 14px;
  border-radius: 12px;
  background: #111;
  color: #fff;
  line-height: 1.6;
  border: 1px solid #333;
}
.scaffold-feedback {
  margin-top: 12px;
}
.scaffold-step-context {
  margin-top: 12px;
}
""",
                cardTemplates=[{"Name": "Scaffold", "Front": SCAFFOLD_FRONT_TEMPLATE, "Back": SCAFFOLD_BACK_TEMPLATE}],
            )

    def ensure_deck(self, deck_name: str) -> None:
        self.create_deck(deck_name)

    def add_card(self, deck_name: str, card: CardDraft) -> None:
        card_type = card.card_type.lower()
        note_tags = []
        if card.source_label:
            note_tags.append(card.source_label.lower().replace(" ", "_"))
        verified = bool(card.extra.get("verification", {}).get("passed", False))
        if verified:
            note_tags.append("verified")
        if card_type == "mcq":
            fields = {
                "Question": card.question,
                "Q_1": card.answer,
                "Q_2": card.distractors[0] if len(card.distractors) > 0 else "",
                "Q_3": card.distractors[1] if len(card.distractors) > 1 else "",
                "Q_4": card.distractors[2] if len(card.distractors) > 2 else "",
                "Answers": card.extra.get("answer_pattern", "1 0 0 0"),
                "QType": card.extra.get("qtype", "2"),
                "Sources": card.source_label,
                "Extra1": card.extra.get("why_this_matters", ""),
                "Tags": card.extra.get("tags", ""),
                "WhyThisMatters": card.extra.get("why_this_matters", ""),
            }
            model_name = "StarCardsMCQInteractive"
        elif card_type == "cloze":
            fields = {"Text": card.question}
            model_name = "Cloze"
        elif card_type == "essay":
            fields = {
                "Question": card.question,
                "Scope": card.extra.get("scope", card.source_label),
                "ModelAnswer": card.answer,
                "KeyTerms": "|".join(card.key_terms),
                "Source": card.source_label,
            }
            model_name = "StarCardsEssay"
        elif card_type == "matching":
            fields = {"Pairs": "|".join(card.extra.get("pairs", [])), "Source": card.source_label}
            model_name = "StarCardsMatchingInteractive"
        elif card_type in ("truefalse", "tf"):
            fields = {
                "Statement": card.question,
                "Answer": card.answer,
                "Correction": card.extra.get("correction", ""),
                "Source": card.source_label,
            }
            model_name = "StarCardsTrueFalseInteractive"
        elif card_type == "scaffold":
            causal_verb = card.extra.get("causal_verb", "")
            if isinstance(causal_verb, list):
                causal_verb = "|".join(str(v) for v in causal_verb if v)
            fields = {
                "Sequence": str(card.extra.get("sequence", card.source_label)),
                "Position": str(card.extra.get("position", 1)),
                "Total": str(card.extra.get("of", 1)),
                "Question": card.question,
                "ModelAnswer": card.answer,
                "KeyTerms": "|".join(card.key_terms),
                "CardType": str(card.extra.get("card_type", "node")),
                "CausalVerb": "" if causal_verb is None else str(causal_verb),
                "Source": card.source_label,
                "PrevQuestion": str(card.extra.get("prev_question", "")),
                "PrevAnswer": str(card.extra.get("prev_answer", "")),
                "NextQuestion": str(card.extra.get("next_question", "")),
                "NextAnswer": str(card.extra.get("next_answer", "")),
            }
            model_name = "StarCardsScaffoldInteractive"
        else:
            fields = {"Text": card.question}
            model_name = "Cloze"

        allow_duplicate = card_type == "scaffold"
        self.invoke(
            "addNote",
            note={
                "deckName": deck_name,
                "modelName": model_name,
                "fields": fields,
                "tags": note_tags,
                "options": {"allowDuplicate": allow_duplicate},
            },
        )

    def export_package(self, deck_name: str, path: Path) -> bool:
        return bool(self.invoke("exportPackage", deck=deck_name, path=str(path), includeSched=self.settings.include_sched))

    def import_package(self, path: Path) -> bool:
        return bool(self.invoke("importPackage", path=str(path)))

    def add_image_to_media(self, image_path: Path, filename: str | None = None) -> str:
        data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        name = filename or image_path.name
        self.invoke("storeMediaFile", filename=name, data=data)
        return name
