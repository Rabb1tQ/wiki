# wiki
由于收集了一堆文档，文档数量及附件过多，现有的免费的系统不满足我的需求，所以自己弄个~

## 功能特点
1. 基于 Markdown 的文档管理
2. 强大的全文搜索功能（支持中文搜索）
3. 文档批量导入和管理
4. 支持文档删除（单个/批量）
5. 支持文档附件管理
6. 简洁的用户界面

## 系统要求
1. Python 3.x
2. Elasticsearch 7.17.0

## 安装步骤

### 1. 安装 Python 依赖
```bash
pip install -r requirements.txt
```

### 2. 安装 Elasticsearch
1. 下载 Elasticsearch 7.17.0：
   - 访问：https://www.elastic.co/downloads/past-releases/elasticsearch-7-17-0
   - 下载对应系统版本的安装包

2. 安装 Elasticsearch：
   - Windows：解压下载的 zip 文件到合适的目录
   - Linux：解压 tar.gz 文件到合适的目录

### 3. 安装 IK 分词器（必需，用于中文搜索）
有两种安装方式：

#### 方式一：在线安装（推荐）
```bash
# 在 Elasticsearch 的 bin 目录下运行：
elasticsearch-plugin install https://get.infini.cloud/elasticsearch/analysis-ik/7.17.0
```

#### 方式二：离线安装
1. 访问 https://release.infinilabs.com/ 下载对应版本的 IK 分词器
2. 在 Elasticsearch 安装目录下创建目录：`plugins/analysis-ik`
3. 解压下载的文件到该目录
4. 重启 Elasticsearch

### 4. 启动服务
1. 启动 Elasticsearch：
   - Windows：运行 `bin\elasticsearch.bat`
   - Linux：运行 `bin/elasticsearch`

2. 启动 Wiki 系统：
```bash
python app.py
```

## 使用说明
1. 将 Markdown 文档放入 `markdown` 目录
2. 运行 `python import_md.py` 导入文档
3. 访问 http://localhost:5000 使用系统

### 文档管理
1. 文档导入：
   - 支持批量导入 Markdown 文件
   - 自动识别和处理文档中的附件引用

2. 文档删除：
   - 单个文档删除：点击文档列表中的删除按钮
   - 批量删除：使用复选框选择多个文档，点击批量删除按钮
   - 删除操作会同时清理：
     * Elasticsearch 索引
     * 原始 Markdown 文件
     * 相关附件文件

3. 文档搜索：
   - 支持全文搜索
   - 支持中文分词搜索
   - 实时搜索结果展示

## 目录结构
```
wiki/
├── markdown/        # Markdown 文档存储目录
├── static/         # 静态资源文件
├── templates/      # HTML 模板文件
├── uploads/        # 附件上传目录
├── app.py         # 主应用程序
├── import_md.py   # 文档导入脚本
└── requirements.txt # Python 依赖清单
```

## 注意事项
1. 确保 Elasticsearch 已启动并可访问（默认地址：http://localhost:9200）
2. 首次使用需要安装 IK 分词器，否则中文搜索功能将无法正常工作
3. 文档更新后需要重新运行 `import_md.py` 以更新索引
4. 删除文档操作不可恢复，请谨慎操作
5. 建议定期备份 `markdown` 和 `uploads` 目录

## 常见问题
1. 如果遇到中文搜索不准确的问题，请检查 IK 分词器是否正确安装
2. 如果文档更新后搜索结果未更新，请重新运行 `import_md.py`
3. 如果启动时报错，请检查：
   - Elasticsearch 是否正在运行
   - 所有 Python 依赖是否正确安装
   - 配置文件中的连接信息是否正确
