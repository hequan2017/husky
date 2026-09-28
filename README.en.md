[简体中文](README.md) | [English](README.en.md)

# husky — A Beginner CMDB System Built with Django

A hands-on tutorial project that builds a CMDB system from scratch with Django: it covers both the MVC (server-rendered templates) and MVVM (decoupled frontend/backend) development styles. Following the six tutorial documents, you can independently build a simple CMDB with user authentication, host asset management, and dynamic menus.

[![Python](https://img.shields.io/badge/Python-3.6+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-3.0-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Introduction

husky is the companion code of the "Django 之入门 CMDB 系统" (Getting Started with a CMDB System in Django) tutorial series. The tutorials start from the base environment, then build the frontend templates, login/logout, and CRUD, and finally move on to a decoupled frontend/backend (Vue + Django REST Framework). It suits readers with basic Python skills who want to get started with Django web development and ops-platform development.

This is a **tutorial project**: code structure and dependency versions prioritize teaching readability (e.g., Django 3.0-era usage with MySQL 5.7). Use it for learning and as a base for your own modifications — not for production as-is.

## ✨ Features

- Login/logout based on Django Auth with an extended AbstractUser user table and self-service password change
- Host (ECS) asset management: full CRUD over hostname, cloud vendor (Alibaba/Tencent/Huawei/AWS, etc.), instance ID, OS version, CPU/memory, and private/public IP fields
- Paginated asset list (django-pure-pagination) with filtered search
- View-level permission control via Django permissions (`PermissionRequiredMixin`)
- Decoupled API: DRF token login plus image captcha (cache-verified, 180-second TTL)
- Dynamic menus: per-user menu and route data served by the `router` app
- DRF token authentication (`/token`) and Swagger API docs (`/docs`)
- The `workflows` app: ticket workflow (Workflow/State/Transition, etc.) models and processing logic, useful as a workflow-engine learning reference

## 🛠 Tech Stack

| Layer | Choice |
| --- | --- |
| Backend | Python, Django 3.0.4, Django REST Framework, MySQL (PyMySQL) |
| Frontend | Bootstrap 3 (template rendering) + Vue/D2Admin (decoupled chapters) |
| Key dependencies | django-bootstrap3, django-pure-pagination, django-cors-headers, captcha, django-filter, django-crispy-forms, django-rest-swagger |

## 🚀 Getting Started

The tutorial environment is described in [doc/1.md](doc/1.md) (CentOS 7.6 / Python 3.6 / MySQL 5.7). To try it locally:

```bash
git clone https://github.com/hequan2017/husky.git
cd husky
pip install -r requirements.txt

# Edit the MySQL connection in DATABASES inside husky/settings.py (database name: husky)
python manage.py makemigrations system asset router workflows
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

- Admin console: <http://127.0.0.1:8000/admin/>
- System home: <http://127.0.0.1:8000/>
- API docs: <http://127.0.0.1:8000/docs>

## 📁 Project Layout

```text
husky/
├── system/       # users, login/logout, password change
├── asset/        # host (ECS) asset CRUD
├── router/       # decoupled login, captcha, and dynamic menu APIs
├── workflows/    # ticket workflow models and processing logic
├── templates/    # Django templates
├── static/       # static assets (Bootstrap, DataTables, etc.)
└── doc/          # six tutorial documents
```

## 📸 Screenshots

![DEMO](doc/images/demo1.png)

![DEMO](doc/images/2-1.png)

## 📚 Tutorial Index

- [Django之入门 CMDB系统  (一) 基础环境](doc/1.md)
- [Django之入门 CMDB系统  (二) 前端模板](doc/2.md)
- [Django之入门 CMDB系统  (三) 登录注销](doc/3.md)
- [Django之入门 CMDB系统  (四) 增删改查](doc/4.md)
- [Django之入门 CMDB系统  (五) 前后端分离之前端](doc/5.md)
- [Django之入门 CMDB系统  (六) 前后端分离之后端](doc/6.md)

## Dynamic Menus and Tickets

* Dynamic menus: implemented in the `router` app; reference article: <https://mp.weixin.qq.com/s?__biz=MzU1OTYzODA4Mw==&mid=2247484250&idx=1&sn=981024ac0580d8a3eba95742bd32b268&chksm=fc157076cb62f960aa9d88e38e584adfd3025f635d296a670f9f8c68a57229e9bd4a1b3e9d20&mpshare=1&scene=1&srcid=&sharer_sharetime=1582904507372&sharer_shareid=ec5f8f73cf3846c67538a33aa69ae2ae#rd>
* Tickets: see the `workflows` app; related article: <https://mp.weixin.qq.com/s?__biz=MzU1OTYzODA4Mw==&mid=2247484255&idx=1&sn=0a9b4cfe2eb8adc33ae4cf2d581f790a&chksm=fc157073cb62f9657336abb43ea0b9e3d2e778ae5e43739ce1a3c33931968004993f1bdc87aa&mpshare=1&scene=1&srcid=&sharer_sharetime=1583566215427&sharer_shareid=ec5f8f73cf3846c67538a33aa69ae2ae#rd>

## 🔗 Related Projects

* Tutorial project: <https://github.com/hequan2017/husky/>
* Decoupled frontend: [hequan2017/panda](https://github.com/hequan2017/panda/), backend: [hequan2017/pandaAdmin](https://github.com/hequan2017/pandaAdmin) (see doc/5.md and doc/6.md)
* The author's other projects: [hequan2017/go-webssh](https://github.com/hequan2017/go-webssh)

## Author / Community

> 作者: 何全，github地址: <https://github.com/hequan2017>   QQ交流群: 620176501

## 📄 License

[MIT](LICENSE)
