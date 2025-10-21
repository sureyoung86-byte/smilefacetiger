from app.agent import handle_user_input
from app.memory.window import WindowMemory

def main():
    memory = WindowMemory(k=6)
    print("=== 天气出行助手（支持短期记忆）===")
    while True:
        user_input = input("你：")
        if user_input.lower() in ["exit", "quit"]:
            break
        memory.add("user", user_input)
        reply = handle_user_input(user_input)
        print("助手：", reply)
        memory.add("assistant", reply)

if __name__ == "__main__":
    main()
