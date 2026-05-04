$body = @{
    question = "test question"
    session_id = "test"
    chat_id = "test_chat"
    history = @()
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/ask" -Method POST -Headers @{"Content-Type"="application/json"; "X-API-Key"="change-me-in-production"} -Body $body

Write-Host "Response:"
Write-Host ($response | ConvertTo-Json)
