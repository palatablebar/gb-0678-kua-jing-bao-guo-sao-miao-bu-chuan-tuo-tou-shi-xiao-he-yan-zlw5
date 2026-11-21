# 接口

模块GET使用仓内样例，模块POST可传csv或rows与context，直接计算当前规则。`/api/runs`使用完整流水线并原子保存，同时把原始字节按 sha256 留存到 raw/（只写不删）。每个阶段返回rows、quarantine、metrics；M1 额外返回 identity（serial_aliases、reused_serials、events）说明原号与事件身份的对应关系；后续阶段还返回累计隔离。`/api/upload`接收multipart文件file。`/api/runs/<id>/archive`只导出一份带清单与证据的CSV。

## 发布与原件

- `POST /api/runs/<id>/publish`：单事务发布。批次须行数对平且归档就绪，否则 422 `UNPUBLISHABLE`，已发布指针保持旧版不变；成功后切换到该批次并返回批次内容（含 published_at）。
- `GET /api/published`：取当前已发布批次；无发布记录返回 404 `NO_PUBLISHED`。
- `GET /api/runs/<id>/raw`：下载该批次原始上传字节，文件名含输入 sha256；原件缺失返回 404 `RAW_MISSING`。

幂等：同输入同参数重跑得到同一 run_id，复用同一 raw 原件，事件全集不增不减。
