"""错误码与业务异常。

错误码按段划分（与参考项目 `ErrorCode` 完全一致），前端据此做差异化处理：

======  ================================  ==========================================
 段位    含义                              前端行为
======  ================================  ==========================================
 0      成功                              正常取 `data`
 1xxx   认证 / 授权                       1001、1002 清 token 并跳登录页；1003 提示无权限
 2xxx   参数校验                          表单字段标红
 3xxx   资源不存在                        提示后刷新列表
 4xxx   业务规则拒绝                      弹错误提示，停留在当前页
 5xxx   系统异常                          提示「系统繁忙」
======  ================================  ==========================================
"""

from __future__ import annotations

from typing import Any


class ErrorCode:
    SUCCESS = 0

    # ---- 1xxx 认证与授权 ----
    LOGIN_FAILED = 1001      # 账号或密码错误（不区分，防账号枚举）
    TOKEN_INVALID = 1002     # Token 缺失/非法/过期
    NO_PERMISSION = 1003     # 已登录但角色不允许

    # ---- 2xxx 参数 ----
    PARAM_ERROR = 2000

    # ---- 3xxx 资源 ----
    NOT_FOUND = 3001

    # ---- 4xxx 业务规则 ----
    COURSE_CLOSED = 4001          # 课程未开放选课
    ALREADY_SELECTED = 4002       # 重复选课
    TIME_CONFLICT = 4003          # 时间冲突
    COURSE_FULL = 4004            # 容量已满
    NOT_SELECTED = 4005           # 未选该课 / 已退课
    COURSE_DELETE_FORBIDDEN = 4006  # 存在引用，禁止删除
    DUPLICATE_KEY = 4007          # 唯一键冲突

    # ---- 5xxx 系统 ----
    SYSTEM_ERROR = 5000


#: 错误码 -> 默认提示语
DEFAULT_MESSAGES: dict[int, str] = {
    ErrorCode.SUCCESS: "ok",
    ErrorCode.LOGIN_FAILED: "账号或密码错误",
    ErrorCode.TOKEN_INVALID: "登录状态已失效，请重新登录",
    ErrorCode.NO_PERMISSION: "没有权限执行该操作",
    ErrorCode.PARAM_ERROR: "请求参数不正确",
    ErrorCode.NOT_FOUND: "资源不存在",
    ErrorCode.COURSE_CLOSED: "该课程未开放选课",
    ErrorCode.ALREADY_SELECTED: "已选过该课程，请勿重复选课",
    ErrorCode.TIME_CONFLICT: "该课程与已选课程上课时间冲突，无法选课",
    ErrorCode.COURSE_FULL: "课程容量已满或已关闭，选课失败",
    ErrorCode.NOT_SELECTED: "尚未选择该课程",
    ErrorCode.COURSE_DELETE_FORBIDDEN: "该记录已被引用，无法删除",
    ErrorCode.DUPLICATE_KEY: "数据已存在，请勿重复提交",
    ErrorCode.SYSTEM_ERROR: "系统繁忙，请稍后重试",
}


class BusinessException(Exception):
    """业务异常。由 Service 层抛出，全局异常处理器转成统一响应体。"""

    def __init__(self, code: int, message: str | None = None, data: Any = None) -> None:
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, "操作失败")
        self.data = data
        super().__init__(self.message)

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"BusinessException(code={self.code}, message={self.message!r})"


#: 便捷构造器（对标参考项目里满地的 `throw new BusinessException(ErrorCode.X, "…")`）
def fail(code: int, message: str | None = None, data: Any = None) -> BusinessException:
    return BusinessException(code, message, data)
