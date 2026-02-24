**HOW TO RUN??**

# Step 1: Go to backend folder
cd C:\Users\Welcome\OneDrive\Desktop\assistant\backend

# Step 2: Start the server
uvicorn main:app --reload --port 8000
```

---

You should see:
```
✅ Connected to Neo4j
✅ Schema initialized successfully
🚀 Assistant backend is live!
INFO:     Uvicorn running on http://127.0.0.1:8000




**TEST:**
Test 1: Chat with Real Dataset User
jsonPOST /chat
{
  "user_id": "U1",
  "message": "What tasks do I have pending?"
}
✅ Expected: Claude replies with Aarav Sharma's actual pending tasks

Test 2: Chat — Ask About Reminders
jsonPOST /chat
{
  "user_id": "U1",
  "message": "What are my reminders for today?"
}
✅ Expected: Claude lists U1's reminders from Neo4j

Test 3: Chat — Ask About Events
jsonPOST /chat
{
  "user_id": "U1",
  "message": "What events do I have coming up?"
}
✅ Expected: Claude lists U1's upcoming events with location

Test 4: Memory Persistence Test
Send two messages back to back:
jsonPOST /chat
{
  "user_id": "U2",
  "message": "I prefer evening study sessions"
}
Then immediately:
jsonPOST /chat
{
  "user_id": "U2",
  "message": "When should I schedule my next study session?"
}
```
✅ Expected: Claude remembers "evening" from first message

---

## Test 5: Full Context Check
```
GET /user/U1/context
```
✅ Expected: Returns memories, habits, tasks, events, reminders all together

---

## Test 6: Memory Recall
```
GET /memory/recall/U1
✅ Expected: Shows all conversations stored for U1

Test 7: Different City User
jsonPOST /chat
{
  "user_id": "U2",
  "message": "Where am I from and what are my high priority tasks?"
}
✅ Expected: Claude mentions Vihaan Sharma, Bangalore, and their high priority tasks

Test 8: Habit Detection
Send the same type of message 3 times:
jsonPOST /chat
{"user_id": "U3", "message": "Set a reminder for me"}
jsonPOST /chat
{"user_id": "U3", "message": "Set a reminder for me"}
jsonPOST /chat
{"user_id": "U3", "message": "Set a reminder for me"}
```
Then check:
```
GET /habits/U3
```
✅ Expected: A habit node created with confidence > 0.6

---

## Test 9: Delete a Memory
First get a memory_id from Test 6, then:
```
DELETE /memory/{memory_id}
```
✅ Expected: `{"status": "deleted"}`

---

## Test 10: Root Health Check
```
GET /
✅ Expected: {"status": "running", "message": "AI Assistant API is live ✅"}
