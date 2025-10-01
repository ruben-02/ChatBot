<?php
require "auth.php";
check_login();
// $backendUrl = "http://localhost:8080";
// $backendUrl = getenv('BACKEND_URL') ?: "http://localhost:5000";
$backendUrl = "https://chatbot-sb0u.onrender.com";
$username = $_SESSION['username'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Chatbot Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<style>
body { padding:20px; }
#chat-box { height:300px; overflow-y:auto; border:1px solid #ccc; padding:10px; border-radius:8px; }
.msg-user { text-align:right; color:blue; margin:5px; }
.msg-bot { text-align:left; color:green; margin:5px; }
</style>
</head>
<body>
<div class="container">

  <div class="d-flex justify-content-between align-items-center mb-3">
    <h1>Welcome, <?php echo htmlspecialchars($_SESSION['fullname']); ?>!</h1>
    <a href="logout.php" class="btn btn-danger">Logout</a>
  </div>

  <p class="text-muted">Manage connectors and chat with your datasource.</p>

  <!-- Connector Setup -->
  <div class="card p-4 mb-4">
    <h4>Connector Setup</h4>
    <div class="row">
      <div class="col-md-6 mb-3">
        <label class="form-label">Datasource</label>
        <select id="datasource" class="form-select"><option value="">--Select--</option></select>
      </div>
      <div class="col-md-6 mb-3">
        <label class="form-label">Subproduct</label>
        <select id="subproduct" class="form-select"><option value="">--Select--</option></select>
      </div>
    </div>
    <label class="form-label">Config (JSON)</label>
    <textarea id="config" class="form-control mb-3" rows="3" placeholder='{"access_token":"..."}'></textarea>
    <input id="connector_id" class="form-control mb-3" placeholder="Connector ID">
    <button id="btnConnect" class="btn btn-primary">Save Connector</button>
    <button id="btnTest" class="btn btn-outline-secondary">Test Connection</button>
  </div>

  <!-- Saved Connectors -->
<div class="card p-4 mb-4">
  <h4>Saved Connectors</h4>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th>Chatbot Name</th>
          <th>Connector ID</th>
          <th class="text-end">Actions</th>
        </tr>
      </thead>
      <tbody id="saved-connectors"></tbody>
    </table>
  </div>
</div>

<!-- Chat Section -->
<div class="card p-4">
  <h4>Chat</h4>
  <div id="chat-box"></div>
  <div class="input-group mt-2">
    <input id="message" class="form-control" placeholder="Ask something...">
    <button id="btnSend" class="btn btn-success">Send</button>
    <button id="btnClear" class="btn btn-danger">Clear</button>
  </div>
</div>

</div>

<script>
let backend = "<?php echo $backendUrl; ?>";
let currentConnector = null;
let currentChatbotId = null;
let username = "<?php echo $username; ?>";

$(function() {

  // 1️⃣ Load datasources
  $.get(backend + "/datasources")
    .done(function(data){
      $("#datasource").empty().append('<option value="">--Select--</option>');
      for(const [key,val] of Object.entries(data)){
        $("#datasource").append('<option value="'+key+'">'+val.label+'</option>');
      }
    });

  // 2️⃣ Populate subproducts when datasource changes
  $("#datasource").on("change", function() {
    let ds = $(this).val();
    $("#subproduct").empty().append('<option value="">--Select--</option>');
    if(!ds) return;
    $.get(backend + "/datasources", function(data){
      let subs = data[ds].subproducts.filter(sp => sp !== "Todo");
      subs.forEach(sp => $("#subproduct").append('<option value="'+sp+'">'+sp+'</option>'));
    });
  });

  // 3️⃣ Load existing chatbots & connectors
  function loadSavedConnectors(){
    $("#saved-connectors").empty();
    $.get(backend + "/list_chatbots/" + username)
      .done(function(data){
        data.forEach(bot => {
          currentChatbotId = bot.id; // default to last one
          currentConnector = bot.connector_id; // default connector
          $("#saved-connectors").append(`
            <tr>
              <td>${bot.chatbot_name}</td>
              <td>${bot.connector_id}</td>
              <td class="text-end">
                <button class="btn btn-sm btn-secondary test-connector" data-id="${bot.connector_id}">
                  <i class="bi bi-play-circle"></i> Test
                </button>
                <button class="btn btn-sm btn-primary select-connector" data-id="${bot.connector_id}">
                  <i class="bi bi-check-circle"></i> Use
                </button>
                <button class="btn btn-sm btn-danger delete-connector" data-id="${bot.connector_id}">
                  <i class="bi bi-trash"></i> Delete
                </button>
              </td>
            </tr>
          `);
        });
      });
  }

  // Test connector from table (attach only once, outside loader)
  $(document).off("click", ".test-connector").on("click", ".test-connector", function(){
    let connectorId = $(this).data("id");
    $.get(backend+"/test_connection/"+connectorId)
      .done(function(res){
        alert("Connection result: "+JSON.stringify(res).substring(0,200));
      })
      .fail(function(){
        alert("Failed to test connection.");
      });
  });
  loadSavedConnectors();



  

  // Select saved connector
  $(document).on("click", ".select-connector", function(){
    currentConnector = $(this).data("id");
    currentChatbotId = "bot-"+currentConnector;
    alert("Selected connector: " + currentConnector);
  });

  // Delete saved connector
  $(document).on("click", ".delete-connector", function(){
    let connectorId = $(this).data("id");
    let chatbotId = "bot-" + connectorId;
    if(confirm("Are you sure you want to delete this connector and its chatbot?")) {
      $.ajax({
        url: backend + "/delete_chatbot/" + chatbotId,
        type: "DELETE",
        success: function(res) {
          alert("Deleted successfully!");
          loadSavedConnectors();
        },
        error: function(xhr) {
          alert("Failed to delete: " + (xhr.responseJSON?.error || xhr.statusText));
        }
      });
    }
  });

  // 4️⃣ Save connector and chatbot
  $("#btnConnect").click(function(){
    let connectorId = $("#connector_id").val().trim();
    let datasource = $("#datasource").val();
    let subproduct = $("#subproduct").val();
    if(!connectorId || !datasource || !subproduct) return alert("Fill all fields!");

    let config = {};
    try { config = JSON.parse($("#config").val()); } catch(e){ return alert("Invalid JSON"); }

    $.ajax({
      url: backend+"/connect",
      type:"POST",
      contentType:"application/json",
      data: JSON.stringify({
        connector_id: connectorId,
        username: username,
        datasource: datasource,
        subproduct: subproduct,
        config: config
      }),
      success:function(res){
        alert("Connector saved!");
        currentConnector = connectorId;

        // Save chatbot automatically
        $.ajax({
          url: backend+"/save_chatbot",
          type:"POST",
          contentType:"application/json",
          data: JSON.stringify({
            id: "bot-"+connectorId,
            username: username,
            chatbot_name: "MyBot",
            gemini_api_key: "AIzaSyB7MrpFiMoRM9O7S9DNS1gBCUWfxa0PMe4",
            connector_id: connectorId
          }),
          success:function(res){
            currentChatbotId = res.chatbot_id || "bot-"+connectorId;
            alert("Chatbot created and ready to chat!");
            loadSavedConnectors(); // refresh saved connectors list
          }
        });
      }
    });
  });

  // 5️⃣ Test connection
  $("#btnTest").click(function(){
    if(!currentConnector) return alert("Save connector first!");
    $.get(backend+"/test_connection/"+currentConnector)
      .done(function(res){ alert("Connection result: "+JSON.stringify(res).substring(0,200)); });
  });


  // Chat send function (for button and enter key)
  function sendChatMessage() {
    let msg = $("#message").val().trim();
    if(!msg) return alert("Enter a message!");
    if(!currentChatbotId) return alert("Save connector first!");

    $("#chat-box").append('<div class="msg-user">You: '+msg+'</div>');
    $("#message").val("");

    // Add processing animation
    let processingId = "processing-" + Date.now();
    $("#chat-box").append('<div class="msg-bot" id="'+processingId+'">Bot: <span class="dots">...</span></div>');
    $("#chat-box").scrollTop($("#chat-box")[0].scrollHeight);

    // Animate the dots
    let dotCount = 0;
    let dotInterval = setInterval(function() {
      dotCount = (dotCount + 1) % 4;
      let dots = Array(dotCount + 1).join('.') || '.';
      $("#"+processingId+" .dots").text(dots);
    }, 400);

    $.ajax({
      url: backend+"/chat",
      type:"POST",
      contentType:"application/json",
      data: JSON.stringify({ chatbot_id: currentChatbotId, message: msg }),
      success:function(res){
        clearInterval(dotInterval);
        $("#"+processingId).replaceWith('<div class="msg-bot">Bot: '+res.reply+'</div>');
        $("#chat-box").scrollTop($("#chat-box")[0].scrollHeight);
      },
      error:function(){
        clearInterval(dotInterval);
        $("#"+processingId).replaceWith('<div class="msg-bot text-danger">Error connecting to bot</div>');
      }
    });
  }

  $("#btnSend").click(sendChatMessage);

  // Send on Enter key in chat input
  $("#message").on("keydown", function(e) {
    if(e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  // Clear chat functionality
  $("#btnClear").click(function(){
    $("#chat-box").empty();
  });

});
</script>


</body>
</html>
