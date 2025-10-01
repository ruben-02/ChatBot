<?php
require "auth.php";
// $backendUrl = "http://localhost:8080";
$backendUrl = "https://chatbot-sb0u.onrender.com";

$error = "";

if(isset($_SESSION['username'])){
    header("Location: index.php");
    exit;
}

if($_SERVER['REQUEST_METHOD'] === "POST"){
    $username = trim($_POST['username']);
    $password = trim($_POST['password']);
    $db = get_db();
    $stmt = $db->prepare("SELECT * FROM users WHERE username=?");
    $stmt->execute([$username]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if($user && password_verify($password, $user['password'])){
        $_SESSION['username'] = $user['username'];
        $_SESSION['fullname'] = $user['fullname'];
        header("Location: index.php");
        exit;
    } else {
        $error = "Invalid username or password!";
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Login - Chatbot Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<div class="container" style="max-width:400px; margin-top:80px;">
<h2 class="mb-4">Login</h2>
<?php if($error): ?>
    <div class="alert alert-danger"><?php echo $error; ?></div>
<?php endif; ?>
<form method="POST">
    <div class="mb-3">
        <label class="form-label">Email / Username</label>
        <input type="email" class="form-control" name="username" required>
    </div>
    <div class="mb-3">
        <label class="form-label">Password</label>
        <input type="password" class="form-control" name="password" required>
    </div>
    <button class="btn btn-primary w-100" type="submit">Login</button>
    <p class="mt-2">Don't have an account? <a href="signup.php">Signup here</a></p>
</form>
</div>
</body>
</html>
