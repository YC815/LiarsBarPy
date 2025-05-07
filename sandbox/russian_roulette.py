import random


def russian_roulette():
    """
    6 格彈膛（編號 1–6）
    - 子彈隨機放在 1–6 的某格
    - 起始彈膛也隨機選擇 1–6
    - 每按一次 Enter 扣一次板機向下一格旋轉（6→1）
    - 中彈時顯示子彈與起始位置，遊戲結束
    """
    # 隨機決定子彈與初始彈膛位置
    bullet_position = random.randint(0, 5)
    start_position = 0
    current_chamber = start_position

    print("=== 俄羅斯輪盤 ===")
    print("子彈和起始彈膛位置已隱藏，直到中彈才會揭曉。")
    print("按 Enter 扣板機，直到中彈。")

    while True:
        input()  # 等待使用者按 Enter
        print(f"🔫 扣板機！目前彈膛位置：{current_chamber}", end=" — ")
        if current_chamber == bullet_position:
            print("💥 砰！中彈了…遊戲結束")
            print(f"\n── 檢視結果 ──")
            print(f"• 初始子彈位置：{bullet_position}")
            print(f"• 初始彈膛位置：{start_position}")
            break
        else:
            print("空轉，安全！")
            # 旋轉到下一格（6→1）
            current_chamber = current_chamber % 5 + 1


if __name__ == "__main__":
    russian_roulette()
