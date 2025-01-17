fosu操作系统大作业

项目概述：轻量级文件系统 (LightFS) 设计与实现

一、项目背景

操作系统课程期末大作业

二、核心需求分析

单文件存储：
LightFS 将所有的元数据及用户数据统一存放在名为 "light.fs" 的单个文件内。
文件大小固定为256MB，其中前56MB用于保存文件系统的必要信息（如超级块、位图等），后200MB作为数据区，每个数据单元大小为1MB。

接口要求：
用户可以通过命令行界面或者图形界面来操作LightFS。
提供一个或多个可执行程序，以满足不同用户的习惯和需求。

功能需求：
初始化：创建并格式化 "light.fs" 文件。

文件管理：支持文件的创建、重命名、删除、列出所有文件、显示文件内容等基本操作。

数据交互：允许外部文件导入至LightFS以及从LightFS导出文件到外部。

空间管理：提供已用空间与空闲空间的统计信息。

实现说明：
存储布局可以根据团队的设计灵活调整，既可以采用顺序排列，也可以引入目录结构。
支持类FAT的链表结构或位图/索引节点方式来跟踪数据块的分配情况。
需要确保文件命名的独特性，避免出现重名文件的问题。

三、设计思路
为了实现上述需求，我们将采取以下设计策略：

初始化：在首次运行时，检查是否已存在 "light.fs" 文件。如果不存在，则创建该文件并根据预定规则划分出元数据区和数据区，同时设置初始状态（如清零或填充默认值）。

文件操作：通过定义一组API函数来处理文件的创建、读取、更新、删除（CRUD）操作。对于文件名冲突问题，可以在创建新文件时进行检测，并提示用户更改文件名或自动添加唯一标识符。

数据交互：实现文件导入导出功能，使得用户可以方便地将本地文件迁移到LightFS中，反之亦然。

空间管理：维护一个位图或其他形式的数据结构来记录哪些数据块已被占用，哪些仍然可用。当用户请求创建新文件或写入数据时，系统会自动查找合适的空闲位置；删除文件后，相应位置会被标记为空闲，以便后续复用。

四、预期成果

本项目完成后，将能够提供一个完整且易于使用的轻量级文件系统原型，用户可以通过图形界面对文件进行管理

