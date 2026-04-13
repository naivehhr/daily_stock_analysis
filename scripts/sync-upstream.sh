#!/bin/bash
# 同步上游仓库更新
# 用法: ./scripts/sync-upstream.sh

set -e

echo "🔄 开始同步上游更新..."

# 检查是否已添加 upstream
if ! git remote | grep -q "upstream"; then
    echo "📝 未找到 upstream 远程仓库，正在添加..."
    git remote add upstream https://github.com/ZhuLinsen/daily_stock_analysis.git
    echo "✅ upstream 添加成功"
else
    echo "✅ upstream 远程仓库已存在"
fi

# 获取上游更新
echo "📥 获取上游更新..."
git fetch upstream

# 显示当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 当前分支: $CURRENT_BRANCH"

# 如果不在 main 分支，提示用户
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  警告: 你不在 main 分支上"
    echo "建议切换到 main 分支后再同步"
    read -p "是否切换到 main 分支? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git checkout main
        CURRENT_BRANCH="main"
    else
        echo "❌ 取消同步"
        exit 1
    fi
fi

# 显示将要合并的提交
echo ""
echo "📊 上游最新提交:"
git log upstream/main --oneline -5

# 合并上游更改
echo ""
echo "🔀 合并上游更改到 $CURRENT_BRANCH ..."
git merge upstream/main

# 推送到你的 fork
echo ""
echo "📤 推送到你的 fork (origin)..."
git push origin main

echo ""
echo "✅ 同步完成！"
echo "💡 提示: 以后只需运行 ./scripts/sync-upstream.sh 即可同步上游更新"
