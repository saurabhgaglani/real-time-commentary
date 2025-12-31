@echo off
REM Script to verify Google Cloud secrets are properly configured (Windows version)
REM Run this before deploying to ensure all secrets exist and are accessible

SET PROJECT_ID=563072551472
SET REGION=us-central1

echo ==========================================
echo Verifying Google Cloud Secrets
echo ==========================================
echo.

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: gcloud CLI not found. Please install it first.
    exit /b 1
)

REM Set project
echo Setting project to: %PROJECT_ID%
gcloud config set project %PROJECT_ID%
echo.

REM List all secrets
echo Listing all secrets in project...
gcloud secrets list --project=%PROJECT_ID%
echo.

REM Check gemini-api-key
echo ------------------------------------------
echo Checking secret: gemini-api-key
echo ------------------------------------------
gcloud secrets describe gemini-api-key --project=%PROJECT_ID% >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Secret exists: gemini-api-key
    gcloud secrets describe gemini-api-key --project=%PROJECT_ID% --format="table(name,createTime)"
) else (
    echo [ERROR] Secret does NOT exist: gemini-api-key
)
echo.

REM Check elevenlabs-api-key
echo ------------------------------------------
echo Checking secret: elevenlabs-api-key
echo ------------------------------------------
gcloud secrets describe elevenlabs-api-key --project=%PROJECT_ID% >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Secret exists: elevenlabs-api-key
    gcloud secrets describe elevenlabs-api-key --project=%PROJECT_ID% --format="table(name,createTime)"
) else (
    echo [ERROR] Secret does NOT exist: elevenlabs-api-key
)
echo.

REM Check kafka-client-properties
echo ------------------------------------------
echo Checking secret: kafka-client-properties
echo ------------------------------------------
gcloud secrets describe kafka-client-properties --project=%PROJECT_ID% >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Secret exists: kafka-client-properties
    gcloud secrets describe kafka-client-properties --project=%PROJECT_ID% --format="table(name,createTime)"
    echo.
    echo First 3 lines of kafka-client-properties:
    gcloud secrets versions access latest --secret=kafka-client-properties --project=%PROJECT_ID% | findstr /N "^" | findstr "^[1-3]:"
) else (
    echo [ERROR] Secret does NOT exist: kafka-client-properties
)
echo.

echo ==========================================
echo Checking Cloud Run Services
echo ==========================================
echo.

echo Current Cloud Run services:
gcloud run services list --project=%PROJECT_ID% --region=%REGION% --format="table(name,status,url)"
echo.

echo ==========================================
echo Summary
echo ==========================================
echo.
echo If all secrets exist and are accessible, you're ready to deploy!
echo.
echo To deploy, run:
echo   gcloud builds submit --config=cloudbuild.yaml --project=%PROJECT_ID%
echo.
echo To view logs after deployment:
echo   gcloud run services logs read chess-commentary-consumer --project=%PROJECT_ID% --region=%REGION% --limit=100
echo   gcloud run services logs read chess-commentary-producer --project=%PROJECT_ID% --region=%REGION% --limit=100
echo.

pause
