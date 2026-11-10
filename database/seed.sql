USE ai_mock_interview;

INSERT IGNORE INTO user_info (user_id, user_name, email) VALUES
  (1, '演示用户', 'demo@example.com');

INSERT IGNORE INTO job_role (id, role_code, role_name, description) VALUES
  (1, 'java_backend', 'Java后端开发', '面向 Java 后端开发岗位的模拟面试'),
  (2, 'web_frontend', 'Web前端开发', '面向 Web 前端开发岗位的模拟面试');

INSERT INTO question_bank
  (role_code, question_type, difficulty, title, reference_answer, scoring_points, followup_points, tags)
VALUES
  ('java_backend', 'technical', 2,
   'Spring Boot 自动配置的原理是什么？',
   '通过 @SpringBootConfiguration、@EnableAutoConfiguration 和组件扫描组合启动，自动配置类由条件注解筛选后注册 Bean。',
   '启动注解、自动配置类加载、条件装配、自定义扩展',
   '如何排查某个自动配置没有生效？',
   'spring,自动配置,springboot'),
  ('java_backend', 'technical', 2,
   'MySQL 索引失效的常见场景有哪些？',
   '函数或表达式作用在索引列、隐式类型转换、不满足最左前缀、范围条件后的列、模糊匹配前置通配符等都可能导致索引失效。',
   '失效原因、执行计划、最左前缀、优化方法',
   '如何结合 EXPLAIN 判断问题并验证优化效果？',
   'mysql,索引,优化,sql'),
  ('java_backend', 'scenario', 3,
   '线上接口突然变慢，你会如何排查？',
   '先确认影响范围，再从网关、应用日志、线程池、数据库、缓存和外部依赖逐层定位，并结合指标和链路追踪验证根因。',
   '分层排查、指标、日志、数据库、止损和复盘',
   '如果数据库 CPU 和连接数同时升高，你会优先做什么？',
   '线上问题,性能,排查'),
  ('web_frontend', 'technical', 2,
   'Vue 3 响应式系统与 Vue 2 有什么主要区别？',
   'Vue 3 使用 Proxy 拦截对象操作，通过 effect 进行依赖收集和派发更新；Vue 2 使用 Object.defineProperty，存在数组和新增属性等限制。',
   'Proxy、依赖收集、触发更新、Vue2 差异',
   'computed 和 watch 在依赖与缓存机制上有什么不同？',
   'vue,响应式,proxy'),
  ('web_frontend', 'technical', 2,
   '浏览器从输入 URL 到页面展示经历了什么？',
   '包括 URL 解析、DNS、TCP/TLS、HTTP 请求、HTML/CSS/JS 加载解析、DOM/CSSOM、渲染树、布局、绘制和合成。',
   '网络、解析、渲染流程、阻塞因素',
   '哪些因素会阻塞首屏渲染？',
   '浏览器,渲染,http'),
  ('web_frontend', 'scenario', 3,
   '前端页面首屏加载很慢，你会如何分析和优化？',
   '通过 Performance 和 Network 面板定位资源、网络、接口和渲染瓶颈，再采用压缩、代码分割、懒加载、缓存和图片优化等手段。',
   '定位指标、资源优化、渲染优化、验证结果',
   '如何证明优化前后的收益？',
   '性能优化,首屏,前端');

INSERT INTO learning_resource (role_code, resource_type, title, content, link, tags) VALUES
  ('java_backend', 'article', 'MySQL 索引与执行计划',
   '学习 B+Tree 索引、最左前缀、回表和 EXPLAIN。', NULL, 'mysql,索引,优化'),
  ('java_backend', 'article', 'Spring Boot 条件装配',
   '理解自动配置类、条件注解和自定义 Starter。', NULL, 'spring,自动配置'),
  ('java_backend', 'practice', '线上性能问题复盘模板',
   '按照发现、影响、排查、根因、止损和预防组织回答。', NULL, '性能,排查,项目'),
  ('web_frontend', 'article', 'Vue 3 响应式原理',
   '学习 Proxy、effect、依赖收集和派发更新。', NULL, 'vue,响应式'),
  ('web_frontend', 'article', '浏览器渲染与性能指标',
   '理解 DOM/CSSOM、布局、绘制以及 FCP、LCP 等指标。', NULL, '浏览器,性能'),
  ('web_frontend', 'practice', '前端性能优化实践',
   '从网络、资源、渲染和缓存四个层面建立优化清单。', NULL, '性能优化,前端');

