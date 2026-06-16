package com.intruoyi.maintenance.runtime;

import com.hierynomus.msfscc.fileinformation.FileIdBothDirectoryInformation;
import com.hierynomus.msfscc.FileAttributes;
import com.hierynomus.msdtyp.AccessMask;
import com.hierynomus.mssmb2.SMB2CreateDisposition;
import com.hierynomus.mssmb2.SMB2ShareAccess;
import com.hierynomus.smbj.SMBClient;
import com.hierynomus.smbj.auth.AuthenticationContext;
import com.hierynomus.smbj.connection.Connection;
import com.hierynomus.smbj.session.Session;
import com.hierynomus.smbj.share.DiskShare;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Comparator;
import java.util.Set;
import java.util.List;

@Component
public class RuntimeControlNasBrowser {

    public List<NasEntry> listDirectories(NasConfig config) {
        requireText(config.server(), "NAS server");
        requireText(config.share(), "NAS share");
        requireText(config.username(), "NAS username");
        requireText(config.password(), "NAS password");
        requireText(config.root(), "NAS root");
        try (SMBClient client = new SMBClient(); Connection connection = client.connect(config.server())) {
            AuthenticationContext authentication = new AuthenticationContext(
                    config.username(), config.password().toCharArray(), blankToEmpty(config.domain()));
            Session session = connection.authenticate(authentication);
            try (DiskShare share = (DiskShare) session.connectShare(config.share())) {
                return share.list(config.root()).stream()
                        .filter(RuntimeControlNasBrowser::isRealDirectory)
                        .map(item -> new NasEntry(item.getFileName(), config.root() + "/" + item.getFileName(), true))
                        .sorted(Comparator.comparing(NasEntry::name).reversed())
                        .toList();
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("NAS 浏览失败: " + config.server() + "/" + config.share(), ex);
        }
    }

    public List<NasEntry> listFiles(NasConfig config, String root) {
        requireText(config.server(), "NAS server");
        requireText(config.share(), "NAS share");
        requireText(config.username(), "NAS username");
        requireText(config.password(), "NAS password");
        requireText(root, "NAS root");
        try (SMBClient client = new SMBClient(); Connection connection = client.connect(config.server())) {
            AuthenticationContext authentication = new AuthenticationContext(
                    config.username(), config.password().toCharArray(), blankToEmpty(config.domain()));
            Session session = connection.authenticate(authentication);
            try (DiskShare share = (DiskShare) session.connectShare(config.share())) {
                return share.list(root).stream()
                        .filter(item -> !".".equals(item.getFileName()) && !"..".equals(item.getFileName()))
                        .map(item -> new NasEntry(item.getFileName(), root + "/" + item.getFileName(),
                                (item.getFileAttributes() & FileAttributes.FILE_ATTRIBUTE_DIRECTORY.getValue()) != 0))
                        .sorted(Comparator.comparing(NasEntry::name).reversed())
                        .toList();
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("NAS 浏览失败: " + config.server() + "/" + config.share(), ex);
        }
    }

    public boolean isRegularFile(NasConfig config, String path) {
        String normalized = normalizeNasPath(path);
        String parent = parentPath(normalized);
        String fileName = fileName(normalized);
        return listFiles(config, parent).stream()
                .anyMatch(item -> fileName.equals(item.name()) && !item.directory());
    }

    public String readText(NasConfig config, String path) {
        String normalized = normalizeNasPath(path);
        requireText(normalized, "NAS file path");
        try (SMBClient client = new SMBClient(); Connection connection = client.connect(config.server())) {
            AuthenticationContext authentication = new AuthenticationContext(
                    config.username(), config.password().toCharArray(), blankToEmpty(config.domain()));
            Session session = connection.authenticate(authentication);
            try (DiskShare share = (DiskShare) session.connectShare(config.share());
                 com.hierynomus.smbj.share.File file = share.openFile(
                         normalized.replace("/", "\\"),
                         Set.of(AccessMask.GENERIC_READ),
                         null,
                         Set.of(SMB2ShareAccess.FILE_SHARE_READ, SMB2ShareAccess.FILE_SHARE_WRITE,
                                 SMB2ShareAccess.FILE_SHARE_DELETE),
                         SMB2CreateDisposition.FILE_OPEN,
                         null);
                 InputStream inputStream = file.getInputStream()) {
                return new String(inputStream.readAllBytes(), StandardCharsets.UTF_8);
            }
        } catch (IOException ex) {
            throw new RuntimeControlException("NAS 文件读取失败: " + path, ex);
        }
    }

    private static boolean isRealDirectory(FileIdBothDirectoryInformation item) {
        String name = item.getFileName();
        long attributes = item.getFileAttributes();
        return !".".equals(name) && !"..".equals(name)
                && (attributes & FileAttributes.FILE_ATTRIBUTE_DIRECTORY.getValue()) != 0;
    }

    private static void requireText(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new RuntimeControlException(name + " is required");
        }
    }

    private static String blankToEmpty(String value) {
        return value == null ? "" : value;
    }

    private static String normalizeNasPath(String path) {
        if (path == null) {
            return "";
        }
        return String.join("/", java.util.Arrays.stream(path.replace("\\", "/").split("/"))
                .map(String::trim)
                .filter(part -> !part.isBlank() && !".".equals(part))
                .peek(part -> {
                    if ("..".equals(part)) {
                        throw new RuntimeControlException("NAS path must not contain ..");
                    }
                })
                .toList());
    }

    private static String parentPath(String path) {
        int index = path.lastIndexOf('/');
        return index < 0 ? "" : path.substring(0, index);
    }

    private static String fileName(String path) {
        int index = path.lastIndexOf('/');
        return index < 0 ? path : path.substring(index + 1);
    }

    public record NasConfig(
            String server,
            String share,
            String username,
            String password,
            String domain,
            String root
    ) {
    }

    public record NasEntry(String name, String path, boolean directory) {
        public NasEntry(String name, String path) {
            this(name, path, true);
        }
    }
}
