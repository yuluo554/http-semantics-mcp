"""Generated rule catalogue -- do not edit.

Rendered by ``tools/gen_codes.py`` from ``data/README.md`` section 4, and
compared byte for byte by ``gen_codes --check``. ``CATALOG`` is the same object
as ``references/codes.json``; the constants below are the rule codes, so the
judgement layer can name a rule it emits without spelling a code literal
(decisions D41/D42). ``tools/gates.py:code_literals`` exempts this file and
only this file.

``data/README.md`` section 4 is the single editable source: change the table
and re-run the generator, never edit this module.
"""

CATALOG = {
    'codes': {
        'CACHE_AGE_EXCEEDS_LIFETIME': {
            'meaning': '`current_age >= freshness_lifetime`',
            'prefix': 'CACHE_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9111 §4.2',
                'RFC9111 §4.2.3',
            ],
            'template': 'current_age={current_age} is not below freshness_lifetime={freshness_lifetime}',
        },
        'CACHE_EXPIRES_IN_PAST': {
            'meaning': '`Expires` 早于或等于 `Date`',
            'prefix': 'CACHE_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9111 §5.3',
            ],
            'template': 'Expires={expires} is not later than Date={date}',
        },
        'CACHE_HEURISTIC_FRESHNESS': {
            'meaning': '无显式新鲜度，按启发式计算',
            'prefix': 'CACHE_',
            'severity': 'informational',
            'spec_ref': [
                'RFC9111 §4.2.2',
            ],
            'template': 'no explicit freshness; heuristic freshness_lifetime={freshness_lifetime}',
        },
        'CACHE_INVALID_AGE': {
            'meaning': '`Age` 非非负整数（按 0 处理）',
            'prefix': 'CACHE_',
            'severity': 'informational',
            'spec_ref': [
                'RFC9111 §5.1',
            ],
            'template': 'invalid Age={age}; treated as 0',
        },
        'CACHE_INVALID_MAX_AGE': {
            'meaning': '`max-age` 非非负整数（该指令按不存在处理）',
            'prefix': 'CACHE_',
            'severity': 'informational',
            'spec_ref': [
                'RFC9111 §4.2.1',
            ],
            'template': 'invalid max-age={max_age}; directive ignored',
        },
        'CACHE_MAX_AGE_ZERO': {
            'meaning': '`max-age=0`',
            'prefix': 'CACHE_',
            'severity': 'informational',
            'spec_ref': [
                'RFC9111 §4.2.1',
                'RFC9111 §5.2.2.1',
            ],
            'template': 'max-age=0 makes the response stale immediately',
        },
        'CACHE_MUST_REVALIDATE_STALE': {
            'meaning': 'stale 且 `must-revalidate`',
            'prefix': 'CACHE_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9111 §4.2.4',
                'RFC9111 §5.2.2.2',
            ],
            'template': 'stale response with must-revalidate must not be served',
        },
        'CACHE_NO_CACHE': {
            'meaning': '响应声明 `no-cache`，须回源验证',
            'prefix': 'CACHE_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9111 §5.2.2.4',
            ],
            'template': 'Cache-Control: no-cache requires revalidation',
        },
        'CACHE_NO_STORE': {
            'meaning': '响应声明 `no-store`',
            'prefix': 'CACHE_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9111 §5.2.2.5',
            ],
            'template': 'Cache-Control: no-store forbids reuse',
        },
        'CACHE_STALE_WHILE_REVALIDATE': {
            'meaning': '处于 `stale-while-revalidate` 窗口',
            'prefix': 'CACHE_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC5861 §3',
            ],
            'template': 'stale response is inside the stale-while-revalidate window of {window} seconds',
        },
        'COND_IF_MATCH_FAILED': {
            'meaning': '`If-Match` 不匹配 → 412',
            'prefix': 'COND_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9110 §13.1.1',
                'RFC9110 §13.2.2',
            ],
            'template': 'If-Match did not match any current entity tag',
        },
        'COND_IF_MODIFIED_SINCE_NOT_MODIFIED': {
            'meaning': '未修改 → 304',
            'prefix': 'COND_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9110 §13.1.3',
                'RFC9110 §13.2.2',
            ],
            'template': 'resource was not modified after If-Modified-Since={date}',
        },
        'COND_IF_NONE_MATCH_MATCHED': {
            'meaning': '`If-None-Match` 匹配 → 304/412',
            'prefix': 'COND_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9110 §13.1.2',
                'RFC9110 §13.2.2',
            ],
            'template': 'If-None-Match matched the current entity tag',
        },
        'COND_IF_UNMODIFIED_SINCE_FAILED': {
            'meaning': '`If-Unmodified-Since` 不满足 → 412',
            'prefix': 'COND_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9110 §13.1.4',
                'RFC9110 §13.2.2',
            ],
            'template': 'resource was modified after If-Unmodified-Since={date}',
        },
        'COND_IGNORED_INVALID_DATE': {
            'meaning': '日期格式非法，条件被忽略',
            'prefix': 'COND_',
            'severity': 'informational',
            'spec_ref': [
                'RFC9110 §13.1.3',
            ],
            'template': '{header} is not a valid HTTP-date and was ignored',
        },
        'COND_WEAK_COMPARISON_USED': {
            'meaning': '使用弱比较（`If-None-Match`）',
            'prefix': 'COND_',
            'severity': 'informational',
            'spec_ref': [
                'RFC9110 §13.1.2',
                'RFC9110 §8.8.3.2',
            ],
            'template': 'If-None-Match is evaluated with weak comparison',
        },
        'CORS_DISALLOWED_HEADER_NOT_EXPOSED': {
            'meaning': '请求头未被 `Access-Control-Allow-Headers` 覆盖',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS-preflight fetch',
            ],
            'template': 'request header {header} is not listed in Access-Control-Allow-Headers',
        },
        'CORS_MISSING_ALLOW_CREDENTIALS': {
            'meaning': 'credentials 模式缺少 `Access-Control-Allow-Credentials: true`',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS check',
            ],
            'template': 'credentials=include requires Access-Control-Allow-Credentials: true',
        },
        'CORS_MISSING_ALLOW_HEADERS': {
            'meaning': '预检响应缺少 `Access-Control-Allow-Headers`',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS-preflight fetch',
            ],
            'template': 'preflight response has no Access-Control-Allow-Headers (request header {header})',
        },
        'CORS_MISSING_ALLOW_METHODS': {
            'meaning': '预检响应缺少 `Access-Control-Allow-Methods` 或不含请求方法',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS-preflight fetch',
            ],
            'template': 'preflight response does not allow method {method}',
        },
        'CORS_MISSING_ALLOW_ORIGIN': {
            'meaning': '非 simple 响应缺少 `Access-Control-Allow-Origin`',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS check',
            ],
            'template': 'response has no Access-Control-Allow-Origin (origin={origin})',
        },
        'CORS_MODE_OPAQUE': {
            'meaning': '`no-cors` 模式下响应为 opaque（作 informational，不翻转 decision）',
            'prefix': 'CORS_',
            'severity': 'informational',
            'spec_ref': [
                'Fetch §CORS protocol',
                'Fetch §HTTP fetch',
            ],
            'template': 'no-cors response is opaque; response headers are not visible',
        },
        'CORS_NULL_ORIGIN': {
            'meaning': '`Origin: null` 的判定（含 `Allow-Credentials` 交互）',
            'prefix': 'CORS_',
            'severity': 'informational',
            'spec_ref': [
                'Fetch §CORS check',
                'Fetch §CORS protocol and credentials',
            ],
            'template': 'Origin: null is an opaque origin',
        },
        'CORS_ORIGIN_MISMATCH': {
            'meaning': '`Access-Control-Allow-Origin` 值不匹配请求 Origin',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS check',
            ],
            'template': 'Access-Control-Allow-Origin={allow_origin} does not match origin={origin}',
        },
        'CORS_PREFLIGHT_REQUIRED': {
            'meaning': '请求需要预检但 `is_preflight=false`',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS protocol',
                'Fetch §CORS-preflight fetch',
            ],
            'template': 'method {method} with non-safelisted request headers requires a preflight',
        },
        'CORS_REDIRECT_NOT_SAME_ORIGIN': {
            'meaning': '`same-origin` 模式下跨源重定向（Fetch §HTTP-redirect fetch 的 fetch 模式约束）',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS protocol',
                'Fetch §HTTP-redirect fetch',
            ],
            'template': 'same-origin mode cannot follow a redirect to {target}',
        },
        'CORS_WILDCARD_WITH_CREDENTIALS': {
            'meaning': '`*` 与 `credentials=include` 同时出现',
            'prefix': 'CORS_',
            'severity': 'decisive',
            'spec_ref': [
                'Fetch §CORS check',
                'Fetch §CORS protocol and credentials',
            ],
            'template': 'Access-Control-Allow-Origin=* cannot satisfy credentials=include',
        },
        'VARY_DUPLICATE_FIELD': {
            'meaning': '`Vary` 内重复字段（归一化时去重）',
            'prefix': 'VARY_',
            'severity': 'informational',
            'spec_ref': [
                'RFC9111 §4.1',
            ],
            'template': 'Vary lists {header} more than once; duplicates removed',
        },
        'VARY_FIELD_MISMATCH': {
            'meaning': '字段值不一致导致 miss',
            'prefix': 'VARY_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9111 §4.1',
            ],
            'template': 'Vary field {header} differs between stored and incoming request',
        },
        'VARY_FIELD_MISSING': {
            'meaning': '存储时或请求时缺少 Vary 声明的字段',
            'prefix': 'VARY_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9111 §4.1',
            ],
            'template': 'Vary field {header} is absent on one side',
        },
        'VARY_STAR_NEVER_MATCHES': {
            'meaning': '`Vary: *`',
            'prefix': 'VARY_',
            'severity': 'decisive',
            'spec_ref': [
                'RFC9111 §4.1',
            ],
            'template': 'Vary: * always fails to match',
        },
    },
    'error_codes': {
        'INVALID_HEADER_NAME': 'header 名不符合 RFC 9110 token 字符集',
        'INVALID_HEADER_VALUE': 'header 值无法按规范解析（如 ETag 引号不配对、`w/` 小写前缀）',
        'INVALID_INPUT': '缺必填字段、类型错误、枚举越界',
        'INVALID_TIME_FORMAT': '时间字面量不属于 §4.4 的两种格式',
        'UNSUPPORTED_METHOD': '方法不在允许集合',
    },
    'notes': {
        'allow_credentials_null_origin': {
            'meaning': '`Origin: null` 且 `Access-Control-Allow-Credentials: true`',
            'type': 'bool',
        },
        'max_age_capped_by_client': {
            'meaning': '恒为 `false`：不替浏览器裁剪 `Access-Control-Max-Age`',
            'type': 'bool',
        },
        'wildcard_with_credentials': {
            'meaning': '`Access-Control-Allow-Origin: *` 与 `credentials=include` 同时出现',
            'type': 'bool',
        },
    },
    'preflight_cache_key': {
        'algorithm': 'sha256',
        'canonical_url': 'scheme://host[:port]',
        'hex_prefix': 16,
        'input': 'origin + "\\n" + canonical_url',
    },
    'schema_version': 1,
    'source': 'data/README.md section 4',
    'vary_normalization': {
        'default': {
            'case_sensitive': True,
            'fold_whitespace': True,
            'sort_comma_segments': False,
            'trim': True,
        },
        'fields': {
            'accept': {
                'case_sensitive': False,
                'fold_whitespace': True,
                'sort_comma_segments': True,
                'trim': True,
            },
            'accept-encoding': {
                'case_sensitive': False,
                'fold_whitespace': True,
                'sort_comma_segments': True,
                'trim': True,
            },
            'accept-language': {
                'case_sensitive': False,
                'fold_whitespace': True,
                'sort_comma_segments': True,
                'trim': True,
            },
            'user-agent': {
                'case_sensitive': True,
                'fold_whitespace': False,
                'sort_comma_segments': False,
                'trim': True,
            },
        },
    },
    'verified_spec_refs': [
        'Fetch §CORS check',
        'Fetch §CORS protocol',
        'Fetch §CORS protocol and credentials',
        'Fetch §CORS-preflight cache',
        'Fetch §CORS-preflight fetch',
        'Fetch §HTTP fetch',
        'Fetch §HTTP-redirect fetch',
        'RFC5861 §3',
        'RFC9110 §13.1.1',
        'RFC9110 §13.1.2',
        'RFC9110 §13.1.3',
        'RFC9110 §13.1.4',
        'RFC9110 §13.2.2',
        'RFC9110 §5.6.7',
        'RFC9110 §8.8.3.2',
        'RFC9111 §4.1',
        'RFC9111 §4.2',
        'RFC9111 §4.2.1',
        'RFC9111 §4.2.2',
        'RFC9111 §4.2.3',
        'RFC9111 §4.2.4',
        'RFC9111 §4.3',
        'RFC9111 §5.1',
        'RFC9111 §5.2.2.1',
        'RFC9111 §5.2.2.10',
        'RFC9111 §5.2.2.2',
        'RFC9111 §5.2.2.4',
        'RFC9111 §5.2.2.5',
        'RFC9111 §5.3',
    ],
}

# One constant per rule code.
CACHE_AGE_EXCEEDS_LIFETIME = 'CACHE_AGE_EXCEEDS_LIFETIME'
CACHE_EXPIRES_IN_PAST = 'CACHE_EXPIRES_IN_PAST'
CACHE_HEURISTIC_FRESHNESS = 'CACHE_HEURISTIC_FRESHNESS'
CACHE_INVALID_AGE = 'CACHE_INVALID_AGE'
CACHE_INVALID_MAX_AGE = 'CACHE_INVALID_MAX_AGE'
CACHE_MAX_AGE_ZERO = 'CACHE_MAX_AGE_ZERO'
CACHE_MUST_REVALIDATE_STALE = 'CACHE_MUST_REVALIDATE_STALE'
CACHE_NO_CACHE = 'CACHE_NO_CACHE'
CACHE_NO_STORE = 'CACHE_NO_STORE'
CACHE_STALE_WHILE_REVALIDATE = 'CACHE_STALE_WHILE_REVALIDATE'
COND_IF_MATCH_FAILED = 'COND_IF_MATCH_FAILED'
COND_IF_MODIFIED_SINCE_NOT_MODIFIED = 'COND_IF_MODIFIED_SINCE_NOT_MODIFIED'
COND_IF_NONE_MATCH_MATCHED = 'COND_IF_NONE_MATCH_MATCHED'
COND_IF_UNMODIFIED_SINCE_FAILED = 'COND_IF_UNMODIFIED_SINCE_FAILED'
COND_IGNORED_INVALID_DATE = 'COND_IGNORED_INVALID_DATE'
COND_WEAK_COMPARISON_USED = 'COND_WEAK_COMPARISON_USED'
CORS_DISALLOWED_HEADER_NOT_EXPOSED = 'CORS_DISALLOWED_HEADER_NOT_EXPOSED'
CORS_MISSING_ALLOW_CREDENTIALS = 'CORS_MISSING_ALLOW_CREDENTIALS'
CORS_MISSING_ALLOW_HEADERS = 'CORS_MISSING_ALLOW_HEADERS'
CORS_MISSING_ALLOW_METHODS = 'CORS_MISSING_ALLOW_METHODS'
CORS_MISSING_ALLOW_ORIGIN = 'CORS_MISSING_ALLOW_ORIGIN'
CORS_MODE_OPAQUE = 'CORS_MODE_OPAQUE'
CORS_NULL_ORIGIN = 'CORS_NULL_ORIGIN'
CORS_ORIGIN_MISMATCH = 'CORS_ORIGIN_MISMATCH'
CORS_PREFLIGHT_REQUIRED = 'CORS_PREFLIGHT_REQUIRED'
CORS_REDIRECT_NOT_SAME_ORIGIN = 'CORS_REDIRECT_NOT_SAME_ORIGIN'
CORS_WILDCARD_WITH_CREDENTIALS = 'CORS_WILDCARD_WITH_CREDENTIALS'
VARY_DUPLICATE_FIELD = 'VARY_DUPLICATE_FIELD'
VARY_FIELD_MISMATCH = 'VARY_FIELD_MISMATCH'
VARY_FIELD_MISSING = 'VARY_FIELD_MISSING'
VARY_STAR_NEVER_MATCHES = 'VARY_STAR_NEVER_MATCHES'
