package cpu_reg_package;

    localparam              FPGAClkSpeed               = 40000000;
    localparam              BaudRateCPU                = 230400;
    localparam              address_width              = 16;
    localparam              data_width                 = 32;
    localparam              RAM_Size                   = 10240;
    localparam logic [31:0] Program_CPU_Start_Address  = 32'h0;
    localparam              VersionStringSize          = 64;

    function [(2*address_width)-1:0] add_address (
        input logic [address_width-1:0] start_address,
        input logic [address_width-1:0] end_address
    );
        begin
            add_address[address_width-1:0] = end_address;
            add_address[2*address_width-1:address_width] = start_address;
        end
    endfunction

    //Enter a new enumeration for every new module added to the bus
    typedef enum {
        ram_e = 0,
        version_string_e,
        io_e,
        uart_e,
        test_cdc_e,
        test_cdc2_e,
        // **** Add New Module Entry Here **** //

        num_entries
    } module_bus;

    //Each enumeration gets a start and end address with the start address on the left and the end address on the right
    localparam [2*(address_width*num_entries)-1:0] module_addresses = {
        add_address('h0000, RAM_Size),                       //ram_e
        add_address('h8000, 'h8000+(VersionStringSize-1)*4), //version_string_e
        add_address('h9000, 'h900C),                         //io_e
        add_address('h9100, 'h9110),                         //uart_e
        add_address('h9200, 'h9200),                         //test_cdc_e  
        add_address('h9300, 'h9300)                          //test_cdc2_e

        // **** Add New Module Addresses Here **** //
    };

     function [address_width-1:0] get_address_start (
            input [$clog2(num_entries):0] val
        );
            begin
                get_address_start = module_addresses[(2*((num_entries-1)-val)+1)*address_width +: address_width];
            end
    endfunction

    function [address_width-1:0] get_address_end (
            input [$clog2(num_entries):0] val
        );
            begin
                get_address_end = module_addresses[(2*((num_entries-1)-val))*address_width +: address_width];
            end
    endfunction

    function [address_width-1:0] get_address_mux (
            input [$clog2(num_entries):0] val
        );
            begin
                get_address_mux = module_addresses[val*address_width +: address_width];
            end
    endfunction

    typedef logic [data_width-1:0] data_reg_inputs_t [0:num_entries-1];

endpackage