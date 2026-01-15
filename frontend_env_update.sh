#!/bin/bash
# Update frontend to use cloud backend URL
sed -i 's|http://127.0.0.1:8000|https://chess-commentary-backend-zph6bbw55a-uc.a.run.app|g' frontend/src/App.jsx
sed -i 's|http://127.0.0.1:8000|https://chess-commentary-backend-zph6bbw55a-uc.a.run.app|g' frontend/src/components/CommentaryChessBoard.jsx
sed -i 's|ws://127.0.0.1:8000|wss://chess-commentary-backend-zph6bbw55a-uc.a.run.app|g' frontend/src/hooks/useCommentary.js