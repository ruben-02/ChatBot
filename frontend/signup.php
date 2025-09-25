<?php
require "auth.php";
$backendUrl = "http://localhost:8080";
$error = "";

if($_SERVER['REQUEST_METHOD'] === "POST"){
    $username = trim($_POST['username']);
    $password = trim($_POST['password']);
    $fullname = trim($_POST['fullname']);

    if(!$username || !$password || !$fullname){
        $error = "All fields are required";
    } else {
        $db = get_db();
        $stmt = $db->prepare("SELECT * FROM users WHERE username=?");
        $stmt->execute([$username]);
        if($stmt->fetch()){
            $error = "User already exists";
        } else {
            $stmt = $db->prepare("INSERT INTO users (username,password,fullname) VALUES (?,?,?)");
            $stmt->execute([$username, password_hash($password,PASSWORD_DEFAULT), $fullname]);
            $_SESSION['username'] = $username;
            $_SESSION['fullname'] = $fullname;
            header("Location: index.php");
            exit;
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Signup - Chatbot Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
<div class="container" style="max-width:400px; margin-top:80px;">
<h2 class="mb-4">Signup</h2>
<?php if($error): ?>
    <div class="alert alert-danger"><?php echo $error; ?></div>
<?php endif; ?>
<form method="POST">
    <div class="mb-3">
        <label class="form-label">Full Name</label>
        <input type="text" class="form-control" name="fullname" required>
    </div>
    <div class="mb-3">
        <label class="form-label">Email / Username</label>
        <input type="email" class="form-control" name="username" required>
    </div>
    <div class="mb-3">
        <label class="form-label">Password</label>
        <input type="password" class="form-control" name="password" required>
    </div>
    <button class="btn btn-primary w-100" type="submit">Signup</button>
    <p class="mt-2">Already have an account? <a href="login.php">Login here</a></p>
</form>
</div>
</body>
</html>
