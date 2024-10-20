# Nginx Events Directives Explained

The `events` block in an Nginx configuration file is used to set global options affecting how Nginx handles connections at a general level. Here's a comprehensive list of directives that can be added to the `events` block:

1. **worker_connections**
   - Syntax: `worker_connections number;`
   - Default: 512
   - Context: events
   - Description: Sets the maximum number of simultaneous connections that can be opened by a worker process.

   Example:
   ```nginx
   worker_connections 1024;
   ```

2. **use**
   - Syntax: `use method;`
   - Default: Depends on the platform
   - Context: events
   - Description: Specifies the connection processing method to use. The available methods depend on the platform and include:
     - `epoll`: Efficient method for Linux 2.6+
     - `kqueue`: Efficient method for FreeBSD, OpenBSD, NetBSD, and macOS
     - `select`: Standard method, less efficient but widely supported
     - `poll`: Similar to select, but can handle more connections
     - `eventport`: Efficient method for Solaris 10+

   Example:
   ```nginx
   use epoll;
   ```

3. **multi_accept**
   - Syntax: `multi_accept on|off;`
   - Default: off
   - Context: events
   - Description: If enabled, a worker process will accept all new connections at a time, rather than accepting one new connection at a time.

   Example:
   ```nginx
   multi_accept on;
   ```

4. **accept_mutex**
   - Syntax: `accept_mutex on|off;`
   - Default: on
   - Context: events
   - Description: If enabled, worker processes will accept new connections by turn. This can prevent the "thundering herd" problem on some systems.

   Example:
   ```nginx
   accept_mutex off;
   ```

5. **accept_mutex_delay**
   - Syntax: `accept_mutex_delay time;`
   - Default: 500ms
   - Context: events
   - Description: If `accept_mutex` is enabled, specifies the maximum time a worker process will wait before trying to acquire the accept mutex again.

   Example:
   ```nginx
   accept_mutex_delay 100ms;
   ```

6. **worker_aio_requests**
   - Syntax: `worker_aio_requests number;`
   - Default: 32
   - Context: events
   - Description: Sets the maximum number of outstanding asynchronous I/O operations for a single worker process.

   Example:
   ```nginx
   worker_aio_requests 64;
   ```

7. **debug_connection**
   - Syntax: `debug_connection address|CIDR|unix:;`
   - Default: —
   - Context: events
   - Description: Enables debugging log for selected client connections.

   Example:
   ```nginx
   debug_connection 127.0.0.1;
   debug_connection 192.168.1.0/24;
   ```

8. **timer_resolution**
   - Syntax: `timer_resolution interval;`
   - Default: —
   - Context: events
   - Description: Reduces timer resolution in worker processes, thus reducing the number of system calls made by gettimeofday().

   Example:
   ```nginx
   timer_resolution 100ms;
   ```

Example of an `events` block using multiple directives:

```nginx
events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
    accept_mutex off;
    worker_aio_requests 64;
    timer_resolution 100ms;
}
```


# Nginx HTTP Directives and Blocks Explained

The `http` block in Nginx configuration is where you define how the server handles HTTP and HTTPS traffic. It can contain numerous directives and nested blocks. Here's a comprehensive overview:

## Main HTTP Block Directives

1. **server_tokens**
   - Syntax: `server_tokens on|off|build|string;`
   - Default: on
   - Description: Enables or disables emitting Nginx version in error messages and "Server" response header field.

   ```nginx
   server_tokens off;
   ```

2. **client_max_body_size**
   - Syntax: `client_max_body_size size;`
   - Default: 1m
   - Description: Sets the maximum allowed size of the client request body.

   ```nginx
   client_max_body_size 10m;
   ```

3. **sendfile**
   - Syntax: `sendfile on|off;`
   - Default: off
   - Description: Enables or disables the use of sendfile().

   ```nginx
   sendfile on;
   ```

4. **keepalive_timeout**
   - Syntax: `keepalive_timeout timeout [header_timeout];`
   - Default: 75s
   - Description: Sets a timeout during which a keep-alive client connection will stay open.

   ```nginx
   keepalive_timeout 65;
   ```

5. **gzip**
   - Syntax: `gzip on|off;`
   - Default: off
   - Description: Enables or disables gzip compression.

   ```nginx
   gzip on;
   ```

## Nested Blocks within HTTP

### 1. server Block

The `server` block defines settings for a specific virtual server.

```nginx
server {
    listen 80;
    server_name example.com;
    root /var/www/example.com;
    
    # Other directives...
}
```

Key directives within `server`:

- **listen**: Specifies the IP address and port the server should listen on.
- **server_name**: Sets names of a virtual server (can use wildcards).
- **root**: Sets the root directory for requests.

### 2. location Block

The `location` block sets configuration depending on the request URI.

```nginx
location /images/ {
    alias /data/images/;
}

location ~ \.php$ {
    fastcgi_pass unix:/var/run/php/php7.4-fpm.sock;
    fastcgi_index index.php;
    include fastcgi_params;
}
```

### 3. upstream Block

The `upstream` block defines a group of servers that can be referenced by `proxy_pass`, `fastcgi_pass`, etc.

```nginx
upstream backend {
    server backend1.example.com weight=5;
    server backend2.example.com;
    server unix:/tmp/backend3;
}
```

## Other Important HTTP Directives

1. **access_log**
   - Syntax: `access_log path [format [buffer=size] [gzip[=level]] [flush=time] [if=condition]];`
   - Description: Sets the path, format, and configuration for a buffered log write.

   ```nginx
   access_log /var/log/nginx/access.log combined;
   ```

2. **error_log**
   - Syntax: `error_log file [level];`
   - Description: Configures logging of errors.

   ```nginx
   error_log /var/log/nginx/error.log warn;
   ```

3. **include**
   - Syntax: `include file | mask;`
   - Description: Includes another file, or files matching the specified mask, into configuration.

   ```nginx
   include /etc/nginx/conf.d/*.conf;
   ```

4. **proxy_pass**
   - Syntax: `proxy_pass URL;`
   - Description: Sets the protocol and address of a proxied server.

   ```nginx
   proxy_pass http://backend;
   ```

5. **ssl_certificate** and **ssl_certificate_key**
   - Syntax: 
     ```nginx
     ssl_certificate file;
     ssl_certificate_key file;
     ```
   - Description: Specifies a file with the certificate and a file with the secret key for SSL/TLS server.

   ```nginx
   ssl_certificate /etc/nginx/ssl/example.com.crt;
   ssl_certificate_key /etc/nginx/ssl/example.com.key;
   ```

6. **add_header**
   - Syntax: `add_header name value [always];`
   - Description: Adds the specified field to a response header.

   ```nginx
   add_header X-Frame-Options "SAMEORIGIN" always;
   ```