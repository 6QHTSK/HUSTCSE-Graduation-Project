# Darpa TC E5 数据集大体介绍

## Event记录分析

`event["datum"]`存储审计记录， 每条审计记录必有且只会有**一个**下面的审计记录类型

### 信息分布情况：

#### 整体情况

- Length: 1217887172
- Start: 2019-05-07 20:44:34
- End: 2019-05-18 05:50:40
- Speed: 1358.09 events/s

|                 Event Name                 |   Count    |
|:------------------------------------------:|:----------:|
|     com.bbn.tc.schema.avro.cdm20.Event     | 1193669198 |
|  com.bbn.tc.schema.avro.cdm20.FileObject   |  10096257  |
|     com.bbn.tc.schema.avro.cdm20.Host      |     3      |
|   com.bbn.tc.schema.avro.cdm20.IpcObject   |  2587751   |
| com.bbn.tc.schema.avro.cdm20.NetFlowObject |   389385   |
|   com.bbn.tc.schema.avro.cdm20.Principal   |    144     |
| com.bbn.tc.schema.avro.cdm20.SrcSinkObject |  4460331   |
|    com.bbn.tc.schema.avro.cdm20.Subject    |  6684103   |

注意，该实验用了三个Host，其中只有cadets1/cadets2参与了正式的攻防测试，cadets3未参与。

- cadets-1 Host UUID: `A3702F4C-5A0C-11E9-B8B9-D4AE52C1DBD3`
- cadets-2 Host UUID: `3A541941-5B04-11E9-B2DB-D4AE52C1DBD3`
- cadets-3 Host UUID: `CB02303B-654E-11E9-A80C-6C2B597E484C`

我们可以认为，2019-05-08 日的记录是绝对良性的，该日数据为系统正常运行时数据，这部分对应gz包为

`ta1-cadets-1-e5-official-2.bin.1.gz` - `ta1-cadets-1-e5-official-2.bin.10.gz`

#### 节点情况

分布在各个主机情况：
- cadets-1 node cnt: 8514653
- cadets-2 node cnt: 6467975
- cadets-3 node cnt: 9235346

com.bbn.tc.schema.avro.cdm20.FileObject Types:
- FILE_OBJECT_DIR : 8607
- FILE_OBJECT_FILE : 9657394
- FILE_OBJECT_UNIX_SOCKET : 430256

com.bbn.tc.schema.avro.cdm20.Host: 3

com.bbn.tc.schema.avro.cdm20.IpcObject Types:
- IPC_OBJECT_PIPE_UNNAMED : 2289463
- IPC_OBJECT_SOCKET_PAIR : 298288

com.bbn.tc.schema.avro.cdm20.NetFlowObject : 389385

com.bbn.tc.schema.avro.cdm20.Principal Types:
- PRINCIPAL_LOCAL : 144

com.bbn.tc.schema.avro.cdm20.SrcSinkObject Types:
- SRCSINK_IPC : 4460331

com.bbn.tc.schema.avro.cdm20.Subject Information Types:
- SUBJECT_PROCESS : 6684103

#### 边情况，以ta1-cadets-1-e5-official-2.bin.100.json为例

- 分布在各个主机情况：
- cadets-1 node cnt: 1138140
- cadets-2 node cnt: 965909
- cadets-3 node cnt: 2810434

事件类型情况：
- EVENT_ACCEPT : 251
- EVENT_ADD_OBJECT_ATTRIBUTE : 499
- EVENT_BIND : 13
- EVENT_CHANGE_PRINCIPAL : 5208
- EVENT_CLOSE : 500765
- EVENT_CONNECT : 1439
- EVENT_CREATE_OBJECT : 9717
- EVENT_EXECUTE : 22124
- EVENT_EXIT : 22330
- EVENT_FCNTL : 114492
- EVENT_FLOWS_TO : 101895
- EVENT_FORK : 22764
- EVENT_LINK : 52
- EVENT_LOGIN : 258
- EVENT_LSEEK : 91836
- EVENT_MMAP : 312295
- EVENT_MODIFY_FILE_ATTRIBUTES : 1140
- EVENT_MODIFY_PROCESS : 208739
- EVENT_MPROTECT : 61993
- EVENT_OPEN : 477890
- EVENT_OTHER : 230
- EVENT_READ : 1118090
- EVENT_RECVFROM : 9163
- EVENT_RECVMSG : 494
- EVENT_RENAME : 5402
- EVENT_SENDMSG : 448
- EVENT_SENDTO : 8915
- EVENT_SIGNAL : 107
- EVENT_TRUNCATE : 1408
- EVENT_UNLINK : 26253
- EVENT_WRITE : 1788273

### 记录类型分辨

- 在Cadets中，存在的记录有
- 会直接产生节点的记录有：所在主机`Host`、用户`Principal`、主体（可执行代码）`Subject`、
  文件客体`FileObject`、IPC客体`IpcObject`、网络流客体`NetFlowObject`、SrcSink客体`SrcSinkObject`
- 会产生边的记录有：事件`Event`

### 不采用数据

#### `Host`

- 数据量：极少
- 标签：`uuid`
- Host节点产生节点，attr：`hostType`（4种）
- Host派生节点：`interface`，2个type
- `interface`标签：`macAddress`
- `interface`标签：`ipAddress`
- 主节点 -> 派生节点：边类型：`interface`

### 节点团

#### `Principal`

- 数据量：极少
- 标签：`uuid`、`userid`
- attr：`PrincipalType`
- 父节点：`group`
- `group`标签：`groupId`

#### `Subject` 可执行文件

- 标签：`uuid`、`cid`
- 类型：`type`: `SUBJECT_PROCESS`,`SUBJECT_THREAD`,`SUBJECT_UNIT`,`SUBJECT_BASIC_BLOCK`,`SUBJECT_OTHER`
- 父节点 `parentSubject`(父节点UUID)
- 父节点 `localPrincipal`(所属用户)

#### `IpcObject`

- 标签 `uuid`
- 类型 `type`: `IPC_OBJECT_PIPE_NAMED`,`IPC_OBJECT_PIPE_UNNAMED`,`IPC_OBJECT_SOCKET_ABSTRACT`,`IPC_OBJECT_SOCKET_PAIR`,`IPC_OBJECT_SOCKET_PATHNAME`,`IPC_OBJECT_SOCKET_UNNAMED`,`IPC_OBJECT_WINDOWS_ALPC`,`IPC_OBJECT_WINDOWS_MAILSLOT`,`IPC_OBJECT_SOCKET_NETLINK`

- 产生边 `uuid1` -> `uuid2`

### 节点

#### `FileObject`

- 标签：`uuid`、`cid`
- 类型：`type`: `FILE_OBJECT_BLOCK`,`FILE_OBJECT_CHAR`,`FILE_OBJECT_DIR`,`FILE_OBJECT_FILE`,`FILE_OBJECT_LINK`,`FILE_OBJECT_PEFILE`,`FILE_OBJECT_UNIX_SOCKET`
- 注：cadets数据集里发现有一些uuid相同的FILE_OBJECT_FILE和FILE_OBJECT_DIR，干脆直接作为FileObject算了

#### `NetFlowObject`

- 标签：`uuid`
- 注：类似套接字有local端和remote端，视情况加入节点

#### `SrcSinkObject`

- 标签： `uuid`
- 类型：`type`一大堆类型，如下

```json
{
  "symbols": [
    "SRCSINK_ACCELEROMETER",
    "SRCSINK_TEMPERATURE",
    "SRCSINK_GYROSCOPE",
    "SRCSINK_MAGNETIC_FIELD",
    "SRCSINK_HEART_RATE",
    "SRCSINK_LIGHT",
    "SRCSINK_PROXIMITY",
    "SRCSINK_PRESSURE",
    "SRCSINK_RELATIVE_HUMIDITY",
    "SRCSINK_LINEAR_ACCELERATION",
    "SRCSINK_MOTION",
    "SRCSINK_STEP_DETECTOR",
    "SRCSINK_STEP_COUNTER",
    "SRCSINK_TILT_DETECTOR",
    "SRCSINK_ROTATION_VECTOR",
    "SRCSINK_GRAVITY",
    "SRCSINK_GEOMAGNETIC_ROTATION_VECTOR",
    "SRCSINK_GPS",
    "SRCSINK_AUDIO",
    "SRCSINK_SYSTEM_PROPERTY",
    "SRCSINK_ENV_VARIABLE",
    "SRCSINK_ACCESSIBILITY_SERVICE",
    "SRCSINK_ACTIVITY_MANAGEMENT",
    "SRCSINK_ALARM_SERVICE",
    "SRCSINK_ANDROID_AUTO",
    "SRCSINK_ANDROID_RADIO",
    "SRCSINK_ANDROID_TV",
    "SRCSINK_ANDROID_VR",
    "SRCSINK_AUDIO_IO",
    "SRCSINK_AUTOFILL",
    "SRCSINK_BACKUP_MANAGER",
    "SRCSINK_BINDER",
    "SRCSINK_BLUETOOTH",
    "SRCSINK_BOOT_EVENT",
    "SRCSINK_BROADCAST_RECEIVER_MANAGEMENT",
    "SRCSINK_CAMERA",
    "SRCSINK_CLIPBOARD",
    "SRCSINK_COMPANION_DEVICE",
    "SRCSINK_COMPONENT_MANAGEMENT",
    "SRCSINK_CONTENT_PROVIDER",
    "SRCSINK_CONTENT_PROVIDER_MANAGEMENT",
    "SRCSINK_DATABASE",
    "SRCSINK_DEVICE_ADMIN",
    "SRCSINK_DEVICE_SEARCH",
    "SRCSINK_DEVICE_USER",
    "SRCSINK_DISPLAY",
    "SRCSINK_DROPBOX",
    "SRCSINK_EMAIL",
    "SRCSINK_EXPERIMENTAL",
    "SRCSINK_FILE",
    "SRCSINK_FILE_SYSTEM",
    "SRCSINK_FILE_SYSTEM_MANAGEMENT",
    "SRCSINK_FINGERPRINT",
    "SRCSINK_FLASHLIGHT",
    "SRCSINK_GATEKEEPER",
    "SRCSINK_HDMI",
    "SRCSINK_IDLE_DOCK_SCREEN",
    "SRCSINK_IMS",
    "SRCSINK_INFRARED",
    "SRCSINK_INSTALLED_PACKAGES",
    "SRCSINK_JSSE_TRUST_MANAGER",
    "SRCSINK_KEYCHAIN",
    "SRCSINK_KEYGUARD",
    "SRCSINK_LOCATION",
    "SRCSINK_LOWPAN",
    "SRCSINK_MACHINE_LEARNING",
    "SRCSINK_MBMS",
    "SRCSINK_MEDIA",
    "SRCSINK_MEDIA_CAPTURE",
    "SRCSINK_MEDIA_LOCAL_MANAGEMENT",
    "SRCSINK_MEDIA_LOCAL_PLAYBACK",
    "SRCSINK_MEDIA_NETWORK_CONNECTION",
    "SRCSINK_MEDIA_REMOTE_PLAYBACK",
    "SRCSINK_MIDI",
    "SRCSINK_NATIVE",
    "SRCSINK_NETWORK",
    "SRCSINK_NETWORK_MANAGEMENT",
    "SRCSINK_NFC",
    "SRCSINK_NOTIFICATION",
    "SRCSINK_OVERLAY_MANAGER",
    "SRCSINK_PAC_PROXY",
    "SRCSINK_PERMISSIONS",
    "SRCSINK_PERSISTANT_DATA",
    "SRCSINK_POSIX",
    "SRCSINK_POWER_MANAGEMENT",
    "SRCSINK_PRINT_SERVICE",
    "SRCSINK_PROCESS_MANAGEMENT",
    "SRCSINK_QUICK_SETTINGS",
    "SRCSINK_RECEIVER_MANAGEMENT",
    "SRCSINK_RCS",
    "SRCSINK_RPC",
    "SRCSINK_SCREEN_AUDIO_CAPTURE",
    "SRCSINK_SERIAL_PORT",
    "SRCSINK_SERVICE_CONNECTION",
    "SRCSINK_SERVICE_MANAGEMENT",
    "SRCSINK_SHORTCUTS",
    "SRCSINK_SMS_MMS",
    "SRCSINK_SPEECH_INTERACTION",
    "SRCSINK_STATUS_BAR",
    "SRCSINK_SYNC_FRAMEWORK",
    "SRCSINK_SYSTEM_UPDATE",
    "SRCSINK_TASK_STACK",
    "SRCSINK_TELEPHONY",
    "SRCSINK_TEST",
    "SRCSINK_TEXT_SERVICES",
    "SRCSINK_THREADING",
    "SRCSINK_TIME_EVENT",
    "SRCSINK_UI",
    "SRCSINK_UID_EVENT",
    "SRCSINK_UI_AUTOMATION",
    "SRCSINK_UI_MODE",
    "SRCSINK_UI_RPC",
    "SRCSINK_USAGE_STATS",
    "SRCSINK_USB",
    "SRCSINK_USER_ACCOUNTS_MANAGEMENT",
    "SRCSINK_USER_INPUT",
    "SRCSINK_VIBRATOR",
    "SRCSINK_WAKE_LOCK",
    "SRCSINK_WALLPAPER_MANAGER",
    "SRCSINK_WAP",
    "SRCSINK_WEB_BROWSER",
    "SRCSINK_WIDGETS",
    "SRCSINK_IPC",
    "SRCSINK_UNKNOWN"
  ]
}
```

### 边 `Event`

- 标签： `uuid`
- 类型：`type`一大堆类型，如下
- 发起方：`subject`
- 目标方：`predicateObject` `predicateObject2`
- 传输字节数：`size`（不全有）

```json
{
  "symbols": [
    "EVENT_ACCEPT",
    "EVENT_ADD_OBJECT_ATTRIBUTE",
    "EVENT_BIND",
    "EVENT_BLIND",
    "EVENT_BOOT",
    "EVENT_CHANGE_PRINCIPAL",
    "EVENT_CHECK_FILE_ATTRIBUTES",
    "EVENT_CLONE",
    "EVENT_CLOSE",
    "EVENT_CONNECT",
    "EVENT_CORRELATION",
    "EVENT_CREATE_OBJECT",
    "EVENT_CREATE_THREAD",
    "EVENT_DUP",
    "EVENT_EXECUTE",
    "EVENT_EXIT",
    "EVENT_FLOWS_TO",
    "EVENT_FCNTL",
    "EVENT_FORK",
    "EVENT_LINK",
    "EVENT_LOADLIBRARY",
    "EVENT_LOGCLEAR",
    "EVENT_LOGIN",
    "EVENT_LOGOUT",
    "EVENT_LSEEK",
    "EVENT_MMAP",
    "EVENT_MODIFY_FILE_ATTRIBUTES",
    "EVENT_MODIFY_PROCESS",
    "EVENT_MOUNT",
    "EVENT_MPROTECT",
    "EVENT_OPEN",
    "EVENT_OTHER",
    "EVENT_READ",
    "EVENT_READ_SOCKET_PARAMS",
    "EVENT_RECVFROM",
    "EVENT_RECVMSG",
    "EVENT_RENAME",
    "EVENT_SENDTO",
    "EVENT_SENDMSG",
    "EVENT_SERVICEINSTALL",
    "EVENT_SHM",
    "EVENT_SIGNAL",
    "EVENT_STARTSERVICE",
    "EVENT_TRUNCATE",
    "EVENT_UMOUNT",
    "EVENT_UNIT",
    "EVENT_UNLINK",
    "EVENT_UPDATE",
    "EVENT_WAIT",
    "EVENT_WRITE",
    "EVENT_WRITE_SOCKET_PARAMS",
    "EVENT_TEE",
    "EVENT_SPLICE",
    "EVENT_VMSPLICE",
    "EVENT_INIT_MODULE",
    "EVENT_FINIT_MODULE"
  ]
}
```

## Ground Truth

在e5实验中，对cadets主机入侵包括一下两个部分

注意：以下时间均为北京时间（CET+8)，ground truth文档的时间为美国东部时间夏令时（CET-4）

### 2019/5/10 10:26 CET-4 Nmap SSH SCP 非法SSH登录【非优先】 （北京时间 5-10 22:26）

该攻击大致是攻击者窃取了登录cadets主机的凭证，非法登录了该主机，并将admin用户文件夹下的信息窃取走

- 发生对应记录gz包：`ta1-cadets-1-e5-official-2.bin.29.gz`
- 发生对应记录json文件：`ta1-cadets-1-e5-official-2.bin.29.json`

该json文件信息如下所示：

- Length: 5000000
- Start: 2019-05-10 22:07:43
- End: 2019-05-10 23:09:49
- Speed: 1342.12 events/s

| Event Name | Count |
| :--------: | :---: |
| com.bbn.tc.schema.avro.cdm20.Event | 4886580 |
| com.bbn.tc.schema.avro.cdm20.FileObject | 61096 |
| com.bbn.tc.schema.avro.cdm20.IpcObject | 9606 |
| com.bbn.tc.schema.avro.cdm20.NetFlowObject | 1464 |
| com.bbn.tc.schema.avro.cdm20.Principal | 3 |
| com.bbn.tc.schema.avro.cdm20.SrcSinkObject | 16260 |
| com.bbn.tc.schema.avro.cdm20.Subject | 24991 |

### 2019/5/16 09:32 Nginx 1.14.2 后门 远程代码执行 （北京时间 5-16 21:26）

该攻击大致是攻击者远程入侵了cadets主机，并执行了一些命令如获得hostname和用户名

- 发生对应记录gz包：`ta1-cadets-1-e5-official-2.bin.100.gz`
- 发生对应记录json文件：`ta1-cadets-1-e5-official-2.bin.100.json`

- Length: 5000000
- Start: 2019-05-16 21:03:06
- End: 2019-05-16 21:37:44
- Speed: 2406.30 events/s

| Event Name | Count |
| :--------: | :---: |
| com.bbn.tc.schema.avro.cdm20.Event | 4914483 |
| com.bbn.tc.schema.avro.cdm20.FileObject | 32772 |
| com.bbn.tc.schema.avro.cdm20.IpcObject | 9696 |
| com.bbn.tc.schema.avro.cdm20.NetFlowObject | 1098 |
| com.bbn.tc.schema.avro.cdm20.Principal | 2 |
| com.bbn.tc.schema.avro.cdm20.SrcSinkObject | 16824 |
| com.bbn.tc.schema.avro.cdm20.Subject | 25125 |

### 2019/5/17 10:16 重复执行上一节入侵 （北京时间 5-17 22:16）

与上一节类似，但是攻击者获取了/etc/passwd等敏感数据，攻击者执行的命令包括hostname, whoami, cat /etc/passwd, whoami,
hostname等等

- 发生对应记录gz包：`ta1-cadets-1-e5-official-2.bin.116.gz` `ta1-cadets-1-e5-official-2.bin.120.gz`
- 发生对应记录json文件：`ta1-cadets-1-e5-official-2.bin.116.json` `ta1-cadets-1-e5-official-2.bin.116.json.1` `ta1-cadets-1-e5-official-2.bin.120.json`

cadets 1 : 关键时间点：10.25 10.26 10.32 15.31 北京时间：22.25 22.26 22.32 5-18 3.31

cadets 2 : 关键时间点：10.47 10.55 11.31 15.31 北京时间：22.47 22.55 23.31 5-18 3.31

记录详情：

#### ta1-cadets-1-e5-official-2.bin.116.json Information:

- Length: 5000000
- Start: 2019-05-17 21:54:24
- End: 2019-05-17 22:39:33
- Speed: 1845.47 events/s

| Event Name | Count |
| :--------: | :---: |
| com.bbn.tc.schema.avro.cdm20.Event | 4884911 |
| com.bbn.tc.schema.avro.cdm20.FileObject | 43446 |
| com.bbn.tc.schema.avro.cdm20.IpcObject | 12968 |
| com.bbn.tc.schema.avro.cdm20.NetFlowObject | 2223 |
| com.bbn.tc.schema.avro.cdm20.SrcSinkObject | 22458 |
| com.bbn.tc.schema.avro.cdm20.Subject | 33994 |

#### ta1-cadets-1-e5-official-2.bin.116.json.1 Information:

- Length: 5000000
- Start: 2019-05-17 22:39:32
- End: 2019-05-17 23:31:21
- Speed: 1608.01 events/s

| Event Name | Count |
| :--------: | :---: |
| com.bbn.tc.schema.avro.cdm20.Event | 4881553 |
| com.bbn.tc.schema.avro.cdm20.FileObject | 45620 |
| com.bbn.tc.schema.avro.cdm20.IpcObject | 13478 |
| com.bbn.tc.schema.avro.cdm20.NetFlowObject | 2123 |
| com.bbn.tc.schema.avro.cdm20.SrcSinkObject | 23023 |
| com.bbn.tc.schema.avro.cdm20.Subject | 34203 |

#### ta1-cadets-1-e5-official-2.bin.120.json Information:
- Length: 5000000
- Start: 2019-05-18 03:02:51
- End: 2019-05-18 03:41:39
- Speed: 2148.25 events/s

| Event Name | Count |
| :--------: | :---: |
| com.bbn.tc.schema.avro.cdm20.Event | 4876752 |
| com.bbn.tc.schema.avro.cdm20.FileObject | 48270 |
| com.bbn.tc.schema.avro.cdm20.IpcObject | 13503 |
| com.bbn.tc.schema.avro.cdm20.NetFlowObject | 1596 |
| com.bbn.tc.schema.avro.cdm20.SrcSinkObject | 23146 |
| com.bbn.tc.schema.avro.cdm20.Subject | 36733 |