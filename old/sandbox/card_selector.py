# menu_selector.py
import readchar
import os

options = ['A', 'B', 'C', 'D', 'E']
current_index = 0
marked = set()
mark_count = 0

def render():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

    display = []
    for i, option in enumerate(options):
        if i == current_index and i in marked:
            display.append(f">[{option}]<")
        elif i == current_index:
            display.append(f"> {option} <")
        elif i in marked:
            display.append(f" [{option}] ")
        else:
            display.append(f"  {option}  ")
    print(" ".join(display))
    print("\n← a / d → 移動游標，space = 標記，q 離開")

while True:
    render()
    key = readchar.readkey()
    if key == 'd':
        current_index = (current_index + 1) % len(options)
    elif key == 'a':
        current_index = (current_index - 1) % len(options)
    elif key == ' ':
        if current_index in marked:
            marked.remove(current_index)
            mark_count -= 1
        else:
            if mark_count >= 3:
                print("最多只能標記三個選項！")
                input("按 Enter 繼續...")
                continue
            else:
                marked.add(current_index)
                mark_count += 1
    elif key == 'q':
        break

print("\n你標記了：", [options[i] for i in marked])
input("按 Enter 關閉視窗...")
