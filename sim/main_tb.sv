`timescale 1ns / 1ns
import cpu_reg_package::*;
module main_tb;

    logic                     clk   = 1'b0;
    logic                     reset = 1'b0;
    logic [31:0]              ex_data_o;
    logic [31:0]              ex_data_i  = '0;
    logic                     uart_tx_o;
    logic                     uart_rx_i;
    logic [7:0]               rx_out;
    logic                     rd_done;
    logic [7:0]               transmit_data;
    logic                     tx_start = 0;
    logic                     tx_busy;
    logic [address_width-1:0] address;
    logic                     we_o;

    integer error_count = 0;

    localparam clk_per = (1/FPGAClkSpeed)*10^9;

    always begin
        #(clk_per/2);
        clk = ~clk;
    end

    task track_errors;
        input string disp;
        begin
            error_count = error_count + 1;
            $display("Error: ", disp);
        end
    endtask

    main_rv32 m1 (
        .clk_i           (clk),
        .reset_i         (reset),
        .external_data_o (ex_data_o),
        .external_data_i (ex_data_i),
        .uart_rx_i       (uart_tx_o),
        .uart_tx_o       (uart_rx_i),
        .address         (address),
        .irq             ('0),
        .cpu_we_o        (we_o)
    );

    uart #(
        .ClkFreq         (FPGAClkSpeed),
        .BaudRate        (BaudRateCPU),
        .ParityBit       ("none"),
        .UseDebouncer    (1),
        .OversampleRate  (16)
    ) uart_testbench_1 (
        .clk_i           (clk),
        .reset_i         (reset),
        .uart_txd_o      (uart_tx_o),
        .uart_rxd_i      (uart_rx_i),
        .data_o          (rx_out),
        .data_valid_o    (rx_done),
        .data_i          (transmit_data),
        .data_valid_i    (tx_start),
        .data_in_ready_o (tx_busy)
    );

    task SendUARTMessage (string messageToSend);
        begin
            foreach (messageToSend[i]) begin
                transmit_data = messageToSend[i];
                tx_start = 1'b1;
                @(posedge clk);
                tx_start = 1'b0;
                @(posedge clk);
                wait (tx_busy == 1);
                repeat(3) @(posedge clk);
            end
        end
    endtask

    task automatic RecvUARTMessage(output string msg);
        automatic byte char_array[$];
        logic received = 0;
        fork
        begin
           while (1) begin
                wait(rx_done == 1);
                char_array.push_back(rx_out);
                wait(rx_done == 0);
                if (rx_out == "\n") break;
            end

            // Construct the string manually
            msg = "";
            foreach (char_array[i]) begin
                msg = {msg, char_array[i]};
            end
            received = 1;
        end
        begin
            repeat(500000) @(posedge clk);
            if (received == 0) begin
                track_errors("Message Not Received!");
            end
        end
        join_any
        
    endtask

    task automatic readVersionFile(output string extracted);
        integer file;
        string line;
        bit inside_quotes;
        
        file = $fopen("../rtl/version_string.svh", "r");
        if (file == 0) begin
            track_errors("Can't Open Version File!");
            extracted = "";
            return;
        end

        // Read only the first line
        if (!$feof(file)) begin
            void'($fgets(line, file));
            inside_quotes = 0;
            extracted = "";

            // Extract characters only inside quotes
            for (int i = 0; i < line.len(); i++) begin
                if (line[i] == "\"") begin
                    inside_quotes = !inside_quotes;
                end else if (inside_quotes) begin
                    extracted = {extracted, line[i]};
                end
            end
            extracted = {extracted, "\n"};
        end

        $fclose(file);
    endtask

    task automatic TestVersionReadBack;
        begin
            string message;
            string version_string;
            SendUARTMessage("readFPGAVersion\n");
            RecvUARTMessage(message);
            readVersionFile(version_string);
            if (message != version_string) begin
                track_errors("Version String Not Correct!");
            end
        end
    endtask

    task TestWriteExternalOutput;
        string msg;  
        int unsigned input_data;  
        string to_send;   
        logic received;   
        begin   
            received = 0;
            input_data = $urandom_range(0,(2**32)-1);
            to_send = $sformatf("wFPGA,%0d,%0d\n", get_address_start(io_e)+4, input_data);
            SendUARTMessage(to_send);
            fork
                begin
                    wait (address == 'h9004);
                    received = 1;
                end
                begin
                    if (received == 0) begin
                        repeat(1500000) @(posedge clk);
                        track_errors("Write Never Received!");
                    end
                end
            join_any
            repeat(2) @(posedge clk);
            if (ex_data_o != input_data) begin
                $display("ex_data_o:  %d", ex_data_o);
                $display("input_data: %d", input_data);
                track_errors("External Output Not Correct!");
            end
        end
    endtask

    task TestReadExternalInput;
        string msg;
        string to_send;
        int num_recv;
        begin
            ex_data_i = $urandom();
            to_send = $sformatf("rFPGA,%0d\n", get_address_start(io_e));
            SendUARTMessage(to_send);
            RecvUARTMessage(msg);
            $sscanf(msg, "%d", num_recv);
            if(num_recv != ex_data_i) begin
                $display("ex_data_i: %d", ex_data_i);
                $display("msg:       %d", msg);
                track_errors("External Input Not Correct!");
            end
        end
    endtask

    initial begin
        reset = 1'b1;
        repeat(10) begin
            @(posedge clk);
        end
        reset = 1'b0;
        repeat(10) begin
            @(posedge clk);
        end
        #50;
        SendUARTMessage("\n");
        repeat(5) begin
            TestVersionReadBack();
            TestWriteExternalOutput();
            TestReadExternalInput();
        end

        if (error_count >= 1) begin
            $display("There were %0d errors!", error_count);
        end else begin
            $display("Testbench Passed!");
        end
        $finish();
    end

endmodule
