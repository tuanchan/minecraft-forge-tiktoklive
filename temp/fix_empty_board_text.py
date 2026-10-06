from pathlib import Path
p=Path('TikTokMobForge/src/main/java/vn/deadchan/tiktokmob/ServerPinnedCommentBoard.java');s=p.read_text(encoding='utf-8').replace('    private static EntityDataAccessor<Component> textAccessor;','')
s=s.replace('                setText(board.header, Component.empty());\n                setText(board.display, commentText(author, text, board.style));','                setTextData(board.display.getEntityData(), commentText(author, text, board.style));')
a=s.index('    private static void setText(');b=s.index('    private static Component titleText',a)
s=s[:a]+'''    /** Resolve the schema, not the non-default values of a particular display.
     * An empty header has no non-default COMPONENT entry at all. */
    private static final class TextData {
        static final EntityDataAccessor<Component> ACCESSOR = resolve();

        @SuppressWarnings("unchecked")
        private static EntityDataAccessor<Component> resolve() {
            for (var field : Display.TextDisplay.class.getDeclaredFields()) {
                if (!java.lang.reflect.Modifier.isStatic(field.getModifiers())
                    || field.getType() != EntityDataAccessor.class) continue;
                try {
                    field.setAccessible(true);
                    var accessor = (EntityDataAccessor<?>) field.get(null);
                    if (accessor.serializer() == EntityDataSerializers.COMPONENT)
                        return (EntityDataAccessor<Component>) accessor;
                } catch (ReflectiveOperationException error) {
                    throw new IllegalStateException("Cannot access TextDisplay text schema", error);
                }
            }
            throw new IllegalStateException("TextDisplay has no COMPONENT accessor");
        }
    }

    static EntityDataAccessor<Component> textDataAccessor() { return TextData.ACCESSOR; }

    static void setTextData(net.minecraft.network.syncher.SynchedEntityData data, Component text) {
        data.set(TextData.ACCESSOR, text);
    }

''' + s[b:];p.write_text(s,encoding='utf-8')
