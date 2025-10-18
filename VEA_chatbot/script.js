const chatBox = document.getElementById("chat-box");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

function appendMessage(sender, message) {
  const row = document.createElement("div");
  row.className = `msg ${sender === "You" ? "me" : "bot"}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = `<strong>${sender}:</strong> ${escapeHTML(message)}`;
  row.appendChild(bubble);
  chatBox.appendChild(row);
  chatBox.scrollTop = chatBox.scrollHeight;
}
function escapeHTML(s){ return s.replace(/[&<>"']/g, m=>({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[m])); }


async function sendMessage(){
  const userMessage = input.value.trim();
  if (!userMessage) return;
  appendMessage("You", userMessage);
  input.value = "";

  try {
    const res = await fetch("http://127.0.0.1:5000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage })
    });
    const data = await res.json();
    appendMessage("VEA", data.reply || data.error || "Sorry, I hit an issue.");
  } catch {
    appendMessage("VEA", "Connection error.");
  }
}

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e)=>{ if (e.key === "Enter") sendMessage(); });
