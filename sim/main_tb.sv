`timescale 1ns / 1ns
import cpu_sim_package::*;
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

    logic [data_width-1:0]    cpu_data_o;
    data_reg_inputs_t         cpu_data_i;
    logic                     cpu_halt_i;

    integer error_count = 0;

    localparam clk_per = (1/FPGAClkSpeed)*10^9;

    always begin
        #(clk_per/2);
        clk = ~clk;
    end

    logic clk_cdc = 1'b0;

    always begin
        #(clk_per/4.26);
        clk_cdc = ~clk_cdc;
    end

    task track_errors;
        input string disp;
        begin
            error_count = error_count + 1;
            $display("Error: ", disp);
            $timeformat(-9, 2, " ns", 10);
            $display("Simulation time is: %t", $time);
        end
    endtask

    cpu_sim_top m1 (
        .clk_i           (clk),
        .reset_i         (reset),
        .external_data_o (ex_data_o),
        .external_data_i (ex_data_i),
        .uart_rx_i       (uart_tx_o),
        .uart_tx_o       (uart_rx_i),
        .address         (address),
        .cpu_data_o      (cpu_data_o),
        .cpu_data_i      (cpu_data_i),
        .cpu_halt_i      (cpu_halt_i),
        .irq_i           ('0),
        .cpu_we_o        (we_o)
    );

    cpu_sim_uart #(
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

    cpu_sim_bus_rv32 cpubus();

    assign cpubus.clk_i     = clk;
    assign cpubus.reset_i   = reset;
    assign cpubus.cpu_reset_o = reset;

    assign cpubus.data_o    = cpu_data_o;
    assign cpu_data_i       = cpubus.data_i;
    assign cpubus.address_o = address;
    assign cpu_halt_i       = cpubus.cpu_halt_i; 
    assign cpubus.we_o      = we_o;

    cpu_sim_bus_rv32 cdc_cpubus [num_entries] ();

    logic cdc_clocks [num_entries];

    assign cdc_clocks[test_cdc_e] = clk_cdc;
    assign cdc_clocks[test_cdc2_e] = clk_cdc;

    cpu_sim_bus_cdc #(
        .bus_cdc_start_address (get_address_start(test_cdc_e)),
        .bus_cdc_end_address   (get_address_end(test_cdc2_e))
    ) cdc_1 (
        .cdc_clks_i (cdc_clocks),
        .cpubus_i   (cpubus),
        .cpubus_o   (cdc_cpubus)
    );

    logic [data_width-1:0] test_cdc_register = '0;
    logic [data_width-1:0] test_cdc2_register = '0;

    always_ff @(posedge clk_cdc) begin
        if (cdc_cpubus[test_cdc_e].we_o == 1'b1) begin
            unique case (cdc_cpubus[test_cdc_e].address_o)
                get_address_start(test_cdc_e) : begin
                    test_cdc_register <= cdc_cpubus[test_cdc_e].data_o;
                end
                default : begin
                    test_cdc_register <= test_cdc_register;
                end
            endcase
        end
    end

    always_ff @(posedge clk_cdc) begin
        if (cdc_cpubus[test_cdc_e].we_o == 1'b0) begin
            unique case (cdc_cpubus[test_cdc_e].address_o)
                get_address_start(test_cdc_e) : begin
                    cdc_cpubus[test_cdc_e].data_i[test_cdc_e] <= test_cdc_register;
                end
                default : begin
                    cdc_cpubus[test_cdc_e].data_i[test_cdc_e] <= '0;
                end
            endcase
        end
    end

    always_ff @(posedge clk_cdc) begin
        if (cdc_cpubus[test_cdc2_e].we_o == 1'b1) begin
            unique case (cdc_cpubus[test_cdc2_e].address_o)
                get_address_start(test_cdc2_e) : begin
                    test_cdc2_register <= cdc_cpubus[test_cdc2_e].data_o;
                end
                default : begin
                    test_cdc2_register <= test_cdc2_register;
                end
            endcase
        end
    end

    always_ff @(posedge clk_cdc) begin
        if (cdc_cpubus[test_cdc2_e].we_o == 1'b0) begin
            unique case (cdc_cpubus[test_cdc2_e].address_o)
                get_address_start(test_cdc2_e) : begin
                    cdc_cpubus[test_cdc2_e].data_i[test_cdc2_e] <= test_cdc2_register;
                end
                default : begin
                    cdc_cpubus[test_cdc2_e].data_i[test_cdc2_e] <= '0;
                end
            endcase
        end
    end

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
                        repeat(25000000) @(posedge clk);
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

    task TestWriteCDCModule;
        string msg;  
        int unsigned input_data;  
        string to_send;   
        logic received;   
        begin   
            received = 0;
            input_data = $urandom_range(0,(2**32)-1);
            to_send = $sformatf("wFPGA,%0d,%0d\n", get_address_start(test_cdc_e), input_data);
            SendUARTMessage(to_send);
            fork
                begin
                    wait (cdc_cpubus[test_cdc_e].address_o == get_address_start(test_cdc_e));
                    received = 1;
                end
                begin
                    if (received == 0) begin
                        repeat(25000000) @(posedge clk_cdc);
                        track_errors("Write Never Received!");
                    end
                end
            join_any
            repeat(2) @(posedge clk_cdc);
            if (test_cdc_register != input_data) begin
                $display("test_cdc_register:  %d", test_cdc_register);
                $display("input_data:         %d", input_data);
                track_errors("CDC Register Write Not Correct!");
            end
        end
    endtask

    task TestReadCDCModule;
        string msg;  
        int unsigned input_data;  
        string to_send;   
        logic received; 
        int num_recv;  
        begin   
            received = 0;
            input_data = $urandom_range(0,(2**32)-1);
            to_send = $sformatf("rFPGA,%0d\n", get_address_start(test_cdc_e));
            SendUARTMessage(to_send);
            RecvUARTMessage(msg);
            $sscanf(msg, "%d", num_recv);
            if (test_cdc_register != num_recv) begin
                $display("test_cdc_register: %d", test_cdc_register);
                $display("msg:               %d", msg);
                track_errors("CDC Register Read Not Correct!");
            end
        end
    endtask

    task TestWriteCDCModule2;
        string msg;  
        int unsigned input_data;  
        string to_send;   
        logic received;   
        begin   
            received = 0;
            input_data = $urandom_range(0,(2**32)-1);
            to_send = $sformatf("wFPGA,%0d,%0d\n", get_address_start(test_cdc2_e), input_data);
            SendUARTMessage(to_send);
            fork
                begin
                    wait (cdc_cpubus[test_cdc2_e].address_o == get_address_start(test_cdc2_e));
                    received = 1;
                end
                begin
                    if (received == 0) begin
                        repeat(25000000) @(posedge clk_cdc);
                        track_errors("Write Never Received!");
                    end
                end
            join_any
            repeat(2) @(posedge clk_cdc);
            if (test_cdc2_register != input_data) begin
                $display("test_cdc2_register:  %d", test_cdc2_register);
                $display("input_data:         %d", input_data);
                track_errors("CDC2 Register Write Not Correct!");
            end
        end
    endtask

    task TestReadCDCModule2;
        string msg;  
        int unsigned input_data;  
        string to_send;   
        logic received; 
        int num_recv;  
        begin   
            received = 0;
            input_data = $urandom_range(0,(2**32)-1);
            to_send = $sformatf("rFPGA,%0d\n", get_address_start(test_cdc2_e));
            SendUARTMessage(to_send);
            RecvUARTMessage(msg);
            $sscanf(msg, "%d", num_recv);
            if (test_cdc2_register != num_recv) begin
                $display("test_cdc2_register: %d", test_cdc2_register);
                $display("msg:               %d", msg);
                track_errors("CDC2 Register Read Not Correct!");
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
            TestWriteCDCModule();
            TestReadCDCModule();
        end
        repeat(10) begin
            TestWriteCDCModule();
            TestReadCDCModule();
        end

        repeat(10) begin
            TestWriteCDCModule2();
            TestReadCDCModule2();
        end

        if (error_count >= 1) begin
            $display("There were %0d errors!", error_count);
        end else begin
            $display("Testbench Passed!");
        end
        $finish();
    end

endmodule
