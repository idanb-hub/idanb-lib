export default {
    initialize({ model }) {
        model.on("msg:custom", (msg) => {
            eval?.(msg);
        });
    },
};
