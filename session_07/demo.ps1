$questions = @(
    "How many branded foods mention sesame in their ingredient declarations?"
    "Which food categories have the most branded foods whose ingredient declarations mention sesame?"
    "How many branded foods have missing ingredient declarations?"
)

foreach ($question in $questions) {
    Clear-Host

    Write-Host "FOOD KNOWLEDGE REPRESENTATION DEMO"
    Write-Host "-----------------------------------"
    Write-Host "Question: $question"
    Write-Host ""

    python .\session_07\ask.py "$question"

    Write-Host ""
    Read-Host "Press Enter to continue to the next question"
}