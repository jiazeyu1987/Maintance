FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY target/rehearsal-app-1.0.0.jar /app/app.jar
USER 10001:10001
ENV JAVA_TOOL_OPTIONS="-Xms64m -Xmx256m -XX:MaxMetaspaceSize=160m -Duser.timezone=Asia/Shanghai"
HEALTHCHECK --interval=10s --timeout=3s --start-period=60s --retries=12 CMD wget -q -O /dev/null http://127.0.0.1:48081/actuator/health || exit 1
ENTRYPOINT ["java","-jar","/app/app.jar"]
