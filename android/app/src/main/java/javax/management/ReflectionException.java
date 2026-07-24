package javax.management;

public class ReflectionException extends JMException {
    private java.lang.Exception exception;

    public ReflectionException(java.lang.Exception e) {
        super();
        this.exception = e;
    }

    public ReflectionException(java.lang.Exception e, String message) {
        super(message);
        this.exception = e;
    }

    public java.lang.Exception getTargetException() {
        return exception;
    }
}
