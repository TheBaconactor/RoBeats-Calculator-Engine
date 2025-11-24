-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:04 PM
-- Time elapsed: 44 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.UDimObjWrapper)
local v_u_2 = require(game.ReplicatedStorage.Shared.RandomLua)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.VArg)
local v_u_6 = require(game.ReplicatedStorage.Shared.Json)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.LVector3)
local v8 = require(game.ReplicatedStorage.Shared.LCFrame)
local v9 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_10 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_12 = require(game.ReplicatedStorage.Shared.BuildConfig)
local s_HttpService_0 = game:GetService("HttpService")
local s_UserInputService_0 = game:GetService("UserInputService")
local s_Players_0 = game:GetService("Players")
local s_TextService_0 = game:GetService("TextService")
local s_TextChatService_0 = game:GetService("TextChatService")
local s_GuiService_0 = game:GetService("GuiService")
local s_CollectionService_0 = game:GetService("CollectionService")
local v_u_177 = {
    ["tobool"] = function(_, p13) --[[ Name: tobool ]] --[[ Line: 26 ]]
        if p13 == 0 then
            return false;
        else
            return p13 and true or false;
        end;
    end,
    ["rad_to_deg"] = function(_, p14) --[[ Name: rad_to_deg ]] --[[ Line: 36 ]]
        return p14 * 180 / 3.141592653589793;
    end,
    ["deg_to_rad"] = function(_, p15) --[[ Name: deg_to_rad ]] --[[ Line: 40 ]]
        return p15 * 3.141592653589793 / 180;
    end,
    ["part_cframe_rotation"] = function(_, p16) --[[ Name: part_cframe_rotation ]] --[[ Line: 56 ]]
        return CFrame.new(-p16.CFrame.p) * p16.CFrame;
    end,
    ["table_clear"] = function(_, p17) --[[ Name: table_clear ]] --[[ Line: 60 ]]
        for v18, _ in pairs(p17) do
            p17[v18] = nil
        end;
    end,
    ["table_to_string"] = function(_, p_u_19) --[[ Name: table_to_string ]] --[[ Line: 64 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): s_HttpService_0 ]]
        local v_u_20 = nil
        pcall(function() --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_6, (copy 3): p_u_19 ]]
            v_u_20 = v_u_6.encode(p_u_19)
        end)
        local v21
        if v_u_20 == nil then
            pcall(function() --[[ Line: 70 ]]
                --[[ Upvalues: (ref 1): v_u_20, (ref 2): s_HttpService_0, (copy 3): p_u_19 ]]
                v_u_20 = s_HttpService_0:JSONEncode(p_u_19)
            end)
            v21 = v_u_20 == nil and "{\"__error__\":true}" or v_u_20
        else
            v21 = v_u_20
        end;
        return v21;
    end,
    ["valv3"] = function(_, p22) --[[ Name: valv3 ]] --[[ Line: 83 ]]
        return Vector3.new(p22, p22, p22);
    end,
    ["get_players"] = function(_) --[[ Name: get_players ]] --[[ Line: 118 ]]
        --[[ Upvalues: (copy 1): s_Players_0 ]]
        return s_Players_0;
    end,
    ["get_default_top_bar_size"] = function(_) --[[ Name: get_default_top_bar_size ]] --[[ Line: 133 ]]
        return 36;
    end,
    ["clamp"] = function(_, p23, p24, p25) --[[ Name: clamp ]] --[[ Line: 266 ]]
        return math.min(p25, (math.max(p24, p23)));
    end,
    ["arg_convert"] = function(_, ...) --[[ Name: arg_convert ]] --[[ Line: 270 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        return v_u_5:arg_convert(...);
    end,
    ["arg_deconvert"] = function(_, ...) --[[ Name: arg_deconvert ]] --[[ Line: 273 ]]
        --[[ Upvalues: (copy 1): v_u_5 ]]
        return v_u_5:arg_deconvert(...);
    end,
    ["tpack"] = function(_, ...) --[[ Name: tpack ]] --[[ Line: 277 ]]
        local v26 = {}
        for v27, v28 in pairs({ ... }) do
            v26[v27] = v28
        end;
        return v26;
    end,
    ["tunpack"] = function(_, p29) --[[ Name: tunpack ]] --[[ Line: 285 ]]
        return unpack(p29);
    end,
    ["dot"] = function(_, p30, p31) --[[ Name: dot ]] --[[ Line: 289 ]]
        return p30.x * p31.x + p30.y * p31.y + p30.z * p31.z;
    end,
    ["comma_value"] = function(_, p32) --[[ Name: comma_value ]] --[[ Line: 310 ]]
        repeat
            local v33
            p32, v33 = string.gsub(p32, "^(-?%d+)(%d%d%d)", "%1,%2")
        until v33 == 0;
        return p32;
    end,
    ["format_ms_time"] = function(_, p34) --[[ Name: format_ms_time ]] --[[ Line: 322 ]]
        local v35 = math.floor(p34)
        return string.format("%d:%d%d", v35 / 60000, v35 / 10000 % 6, v35 / 1000 % 10);
    end,
    ["format_ms_time_hundredth"] = function(_, p36) --[[ Name: format_ms_time_hundredth ]] --[[ Line: 332 ]]
        local v37 = p36 < 0
        local v38 = math.abs((math.floor(p36)))
        local v39 = string.format("%02d:%02d.%03d", math.floor(v38 / 60000), math.floor(v38 % 60000 / 1000), v38 % 1000)
        if v37 then
            v39 = "-" .. v39 or v39
        end;
        return v39;
    end,
    ["format_sec_time"] = function(_, p40) --[[ Name: format_sec_time ]] --[[ Line: 350 ]]
        local v41 = math.floor(p40)
        if v41 > 86400 then
            return string.format("%dd %dh %dm %ds", math.floor(v41 / 86400), math.floor(v41 % 86400) / 3600, math.floor(v41 % 3600) / 60, v41 % 60);
        else
            return string.format("%dh %dm %ds", math.floor(v41 / 3600), math.floor(v41 % 3600) / 60, v41 % 60);
        end;
    end,
    ["connect_once"] = function(_, p42, p_u_43) --[[ Name: connect_once ]] --[[ Line: 379 ]]
        local v_u_44 = nil
        v_u_44 = p42:Connect(function(...) --[[ Line: 381 ]]
            --[[ Upvalues: (ref 1): v_u_44, (copy 2): p_u_43 ]]
            v_u_44:Disconnect()
            p_u_43(...)
        end)
    end,
    ["obj_apply_suffix_alpha_attribute"] = function(_, p45, p46, p47) --[[ Name: obj_apply_suffix_alpha_attribute ]] --[[ Line: 599 ]]
        p45:SetAttribute("Alpha_" .. p46, p47)
    end,
    ["r_set_alpha_v2_flag_as_notraverse"] = function(_, p48) --[[ Name: r_set_alpha_v2_flag_as_notraverse ]] --[[ Line: 621 ]]
        p48:SetAttribute("R_SET_ALPHA_V2_NOTRAVERSE_FLAG", true)
    end,
    ["tra"] = function(_, p49) --[[ Name: tra ]] --[[ Line: 636 ]]
        return 1 - p49;
    end,
    ["do_profile"] = false,
    ["cframe"] = function(_, p50, p51) --[[ Name: cframe ]] --[[ Line: 674 ]]
        return CFrame.new(p50.X, p50.Y, p50.Z) * CFrame.Angles(p51.X * 3.141592653589793 / 180, p51.Y * 3.141592653589793 / 180, p51.Z * 3.141592653589793 / 180);
    end,
    ["flt_cmp_delta"] = function(_, p52, p53, p54) --[[ Name: flt_cmp_delta ]] --[[ Line: 679 ]]
        return math.abs(p52 - p53) < p54;
    end,
    ["udim_obj_wrapper"] = function(_, p55) --[[ Name: udim_obj_wrapper ]] --[[ Line: 713 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:new(p55);
    end,
    ["color3"] = function(_, p56, p57, p58) --[[ Name: color3 ]] --[[ Line: 717 ]]
        return Color3.new(p56 / 255, p57 / 255, p58 / 255);
    end,
    ["color3_to_table"] = function(_, p59) --[[ Name: color3_to_table ]] --[[ Line: 721 ]]
        return {
            ["R"] = math.floor(p59.R * 255),
            ["G"] = math.floor(p59.G * 255),
            ["B"] = math.floor(p59.B * 255)
        };
    end,
    ["color3_from_table"] = function(_, p60) --[[ Name: color3_from_table ]] --[[ Line: 725 ]]
        return Color3.fromRGB(typeof(p60.R) ~= "number" and 0 or p60.R, typeof(p60.G) ~= "number" and 0 or p60.G, typeof(p60.B) ~= "number" and 0 or p60.B);
    end,
    ["timedelta_to_result"] = function(_, p61, p62, p63, p64, p65, p66, p67) --[[ Name: timedelta_to_result ]] --[[ Line: 741 ]]
        --[[ Upvalues: (copy 1): v_u_10 ]]
        local l_NoteResult_Miss_0 = v_u_10.NoteResult_Miss
        if p61 <= p62 and p63 < p61 then
            return v_u_10.NoteResult_Okay;
        end;
        if p61 <= p63 and p64 < p61 then
            return v_u_10.NoteResult_Great;
        end;
        if p61 <= p64 and p65 < p61 then
            return v_u_10.NoteResult_Perfect;
        end;
        if p61 <= p65 and p66 < p61 then
            return v_u_10.NoteResult_Great;
        end;
        if p61 <= p66 and p67 < p61 then
            l_NoteResult_Miss_0 = v_u_10.NoteResult_Okay
        end;
        return l_NoteResult_Miss_0;
    end,
    ["noteresult_list"] = function(_) --[[ Name: noteresult_list ]] --[[ Line: 757 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_10 ]]
        return v_u_3:new({
            v_u_10.NoteResult_Miss,
            v_u_10.NoteResult_Okay,
            v_u_10.NoteResult_Great,
            v_u_10.NoteResult_Perfect
        });
    end,
    ["fill_list_of_direct_children_of_classname"] = function(_, p68, p69, p70) --[[ Name: fill_list_of_direct_children_of_classname ]] --[[ Line: 834 ]]
        for _, v71 in pairs(p68:GetChildren()) do
            if v71.ClassName == p69 then
                p70:push_back(v71)
            end;
        end;
    end,
    ["running_avg"] = function(_, p72, p73, p74) --[[ Name: running_avg ]] --[[ Line: 875 ]]
        return p72 - p72 / p74 + p73 / p74;
    end,
    ["try"] = function(_, p_u_75) --[[ Name: try ]] --[[ Line: 898 ]]
        return xpcall(function() --[[ Line: 899 ]]
            --[[ Upvalues: (copy 1): p_u_75 ]]
            p_u_75()
        end, function(p76) --[[ Line: 901 ]]
            return {
                ["Error"] = p76,
                ["StackTrace"] = debug.traceback()
            };
        end);
    end,
    ["hash_creator"] = function(_, p_u_77) --[[ Name: hash_creator ]] --[[ Line: 955 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        local v_u_78 = {}
        return function(p79) --[[ Line: 957 ]]
            --[[ Upvalues: (copy 1): p_u_77, (copy 2): v_u_78, (ref 3): v_u_2 ]]
            local v80 = p_u_77
            for v81 = 1, #p79 do
                local v82 = string.byte((string.sub(p79, v81, v81)))
                if v_u_78[v82] == nil then
                    v_u_78[v82] = v_u_2.mwc(v82):rand_rangei(1000000, 9000000)
                end;
                v80 = (v80 + v_u_78[v82]) % 10000000
            end;
            return tostring(v80);
        end;
    end,
    ["has_ancestor_of"] = function(_, p83, p84, p85) --[[ Name: has_ancestor_of ]] --[[ Line: 998 ]]
        while p83 ~= nil do
            if p85 ~= nil and p85(p83, p84) == true then
                return true;
            end;
            if p83 == p84 then
                return true;
            end;
            p83 = p83.Parent
        end;
        return false;
    end,
    ["cframe_delta"] = function(_, p86, p87) --[[ Name: cframe_delta ]] --[[ Line: 1009 ]]
        local v88, v89, v90, v91, v92, v93, v94, v95, v96, v97, v98, v99 = p86:components()
        local v100, v101, v102, v103, v104, v105, v106, v107, v108, v109, v110, v111 = p87:components()
        local v112 = v88 - v100
        local v113 = v89 - v101
        local v114 = v90 - v102
        local v115 = v91 - v103
        local v116 = v92 - v104
        local v117 = v93 - v105
        local v118 = v94 - v106
        local v119 = v95 - v107
        local v120 = v96 - v108
        local v121 = v97 - v109
        local v122 = v98 - v110
        local v123 = v99 - v111
        return math.sqrt(v112 * v112 + v113 * v113 + v114 * v114 + v115 * v115 + v116 * v116 + v117 * v117 + v118 * v118 + v119 * v119 + v120 * v120 + v121 * v121 + v122 * v122 + v123 * v123);
    end,
    ["json_encode"] = function(_, p_u_124) --[[ Name: json_encode ]] --[[ Line: 1047 ]]
        --[[ Upvalues: (copy 1): s_HttpService_0 ]]
        local v_u_125 = nil
        local v126, v127 = pcall(function() --[[ Line: 1049 ]]
            --[[ Upvalues: (ref 1): v_u_125, (ref 2): s_HttpService_0, (copy 3): p_u_124 ]]
            v_u_125 = s_HttpService_0:JSONEncode(p_u_124)
        end)
        if v126 == false then
            warn(v127)
        end;
        return v_u_125 == nil and "{}" or v_u_125;
    end,
    ["lookat_camera_cframe"] = function(_, p128, p129) --[[ Name: lookat_camera_cframe ]] --[[ Line: 1073 ]]
        return CFrame.new(p128, p128 + p129:get_normal_dir());
    end,
    ["splist_filter"] = function(_, p130, p131) --[[ Name: splist_filter ]] --[[ Line: 1077 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        local v132 = v_u_3:new()
        for v133 = 1, p130:count() do
            if p131(p130:get(v133), v133) == true then
                v132:push_back(p130:get(v133))
            end;
        end;
        return v132;
    end,
    ["num_string"] = function(_, p134) --[[ Name: num_string ]] --[[ Line: 1087 ]]
        if p134 == 0 then
            return "zero";
        end;
        local v135 = p134 < 0
        local v136 = math.abs(p134)
        local v137 = ""
        local v138 = 0
        local v139 = {
            [0] = "zero",
            [1] = "one",
            [2] = "two",
            [3] = "three",
            [4] = "four",
            [5] = "five",
            [6] = "six",
            [7] = "seven",
            [8] = "eight",
            [9] = "nine"
        }
        while v136 ~= 0 do
            v138 = v138 + 1
            if v138 > 20 then
                return "BRK=" .. v137;
            end;
            local v140 = math.floor(v136 % 10)
            v137 = (v139[v140] == nil and "?" or v139[v140]) .. v137
            v136 = math.floor(v136 / 10)
            if v136 ~= 0 then
                v137 = "_" .. v137
            end;
        end;
        if v135 == true then
            v137 = "negative_" .. v137
        end;
        return v137;
    end,
    ["is_finite"] = function(_, p141) --[[ Name: is_finite ]] --[[ Line: 1144 ]]
        if p141 == nil then
            return false;
        end;
        if type(p141) == "string" then
            p141 = tonumber(p141)
            if p141 == nil then
                return false;
            end;
        elseif type(p141) ~= "number" then
            return false;
        end;
        local v142
        if p141 > (-1 / 0) and p141 < (1 / 0) then
            v142 = p141 == p141
        else
            v142 = false
        end;
        return v142;
    end,
    ["cframe_to_string"] = function(_, p143) --[[ Name: cframe_to_string ]] --[[ Line: 1155 ]]
        local l_p_0 = p143.p
        local l_lookVector_0 = p143.lookVector
        return string.format("CFrame{p(%.2f,%.2f,%.2f) look(%.2f,%.2f,%.2f)}", l_p_0.X, l_p_0.Y, l_p_0.Z, l_lookVector_0.X, l_lookVector_0.Y, l_lookVector_0.Z);
    end,
    ["vec2_to_string"] = function(_, p144) --[[ Name: vec2_to_string ]] --[[ Line: 1161 ]]
        return string.format("Vec2[%.2f]{%.2f,%.2f}", p144.Magnitude, p144.X, p144.Y);
    end,
    ["vec3_to_str"] = function(_, p145) --[[ Name: vec3_to_str ]] --[[ Line: 1165 ]]
        return string.format("Vec3[%.2f]{%.2f,%.2f,%.2f}", p145.Magnitude, p145.X, p145.Y, p145.Z);
    end,
    ["cframe_for_numtable"] = function(_, p146) --[[ Name: cframe_for_numtable ]] --[[ Line: 1169 ]]
        return CFrame.new(p146[1], p146[2], p146[3], p146[4], p146[5], p146[6], p146[7], p146[8], p146[9], p146[10], p146[11], p146[12]);
    end,
    ["enum_val_to_name"] = function(_, p147, p148) --[[ Name: enum_val_to_name ]] --[[ Line: 1173 ]]
        for v149, v150 in pairs(p148) do
            if v150 == p147 then
                return v149;
            end;
        end;
        return "???";
    end,
    ["is_mock_debug_player"] = function(_, p151) --[[ Name: is_mock_debug_player ]] --[[ Line: 1180 ]]
        return type(p151) == "table" and p151.DebugMockPlayer == true;
    end,
    ["gc_count"] = function(_) --[[ Name: gc_count ]] --[[ Line: 1190 ]]
        return collectgarbage("count");
    end,
    ["print_frame_gc"] = false,
    ["print_input_events"] = false,
    ["str_split"] = function(_, p152, p153) --[[ Name: str_split ]] --[[ Line: 1232 ]]
        local v154 = {}
        for v155 in string.gmatch(p152, "([^" .. (p153 == nil and "%s" or p153) .. "]+)") do
            table.insert(v154, v155)
        end;
        return v154;
    end,
    ["string_join"] = function(_, p156, p157, p158, p159) --[[ Name: string_join ]] --[[ Line: 1243 ]]
        return table.concat(p156, p157 == nil and "" or p157, p158 == nil and 1 or p158, p159 == nil and #p156 or p159);
    end,
    ["string_replace"] = function(_, p160, p161, p162) --[[ Name: string_replace ]] --[[ Line: 1250 ]]
        return string.gsub(p160, string.gsub(p161, "[%(%)%.%+%-%*%?%[%]%^%$%%]", "%%%1"), (string.gsub(p162, "[%%]", "%%%%")));
    end,
    ["string_escape_richtext"] = function(_, p163) --[[ Name: string_escape_richtext ]] --[[ Line: 1256 ]]
        return p163:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub("\"", "&quot;"):gsub("\'", "&apos;");
    end,
    ["string_starts_with"] = function(_, p164, p165) --[[ Name: string_starts_with ]] --[[ Line: 1266 ]]
        return string.sub(p164, 1, #p165) == p165;
    end,
    ["string_sub_max_len"] = function(_, p166, p167, p168) --[[ Name: string_sub_max_len ]] --[[ Line: 1270 ]]
        local v169 = p167 == nil and 4096 or p167
        if v169 < #p166 then
            return string.sub(p166, 1, v169) .. (p168 == nil and "..." or p168);
        else
            return p166;
        end;
    end,
    ["transparent_assetid"] = function(_) --[[ Name: transparent_assetid ]] --[[ Line: 1304 ]]
        return "rbxassetid://8099175655";
    end,
    ["gear_assetid"] = function(_) --[[ Name: gear_assetid ]] --[[ Line: 1305 ]]
        return "rbxassetid://6423029758";
    end,
    ["important_assetid"] = function(_) --[[ Name: important_assetid ]] --[[ Line: 1306 ]]
        return "rbxassetid://6560391309";
    end,
    ["semitransparent_assetid"] = function(_) --[[ Name: semitransparent_assetid ]] --[[ Line: 1307 ]]
        return "rbxassetid://792172425";
    end,
    ["get_white_assetid"] = function(_) --[[ Name: get_white_assetid ]] --[[ Line: 1308 ]]
        return "rbxassetid://1547491764";
    end,
    ["placeholder_assetid"] = function(_) --[[ Name: placeholder_assetid ]] --[[ Line: 1309 ]]
        return "rbxasset://textures/ui/GuiImagePlaceholder.png";
    end,
    ["get_question_assetid"] = function(_) --[[ Name: get_question_assetid ]] --[[ Line: 1310 ]]
        return "rbxassetid://1177393947";
    end,
    ["get_sparkle_star_white_assetid"] = function(_) --[[ Name: get_sparkle_star_white_assetid ]] --[[ Line: 1311 ]]
        return "rbxassetid://698514197";
    end,
    ["get_hud_button_chat_assetid"] = function(_) --[[ Name: get_hud_button_chat_assetid ]] --[[ Line: 1312 ]]
        return "rbxassetid://793656907";
    end,
    ["get_new_label_assetid"] = function(_) --[[ Name: get_new_label_assetid ]] --[[ Line: 1313 ]]
        return "rbxassetid://2177736254";
    end,
    ["get_double_arrow_icon_assetid"] = function(_) --[[ Name: get_double_arrow_icon_assetid ]] --[[ Line: 1314 ]]
        return "rbxassetid://1138398504";
    end,
    ["get_icon_eye_assetid"] = function(_) --[[ Name: get_icon_eye_assetid ]] --[[ Line: 1315 ]]
        return "rbxassetid://1622425692";
    end,
    ["get_icon_keybinds_assetid"] = function(_) --[[ Name: get_icon_keybinds_assetid ]] --[[ Line: 1316 ]]
        return "rbxassetid://1211912010";
    end,
    ["plus_add_icon_assetid"] = function(_) --[[ Name: plus_add_icon_assetid ]] --[[ Line: 1317 ]]
        return "rbxassetid://5846248846";
    end,
    ["checkmark_icon_assetid"] = function(_) --[[ Name: checkmark_icon_assetid ]] --[[ Line: 1318 ]]
        return "rbxassetid://792144537";
    end,
    ["x_icon_assetid"] = function(_) --[[ Name: x_icon_assetid ]] --[[ Line: 1319 ]]
        return "rbxassetid://1622427376";
    end,
    ["editor_icon_assetid"] = function(_) --[[ Name: editor_icon_assetid ]] --[[ Line: 1320 ]]
        return "rbxassetid://4831282506";
    end,
    ["editor_text_assetid"] = function(_) --[[ Name: editor_text_assetid ]] --[[ Line: 1321 ]]
        return "rbxassetid://136182315952951";
    end,
    ["thumbs_up_assetid"] = function(_) --[[ Name: thumbs_up_assetid ]] --[[ Line: 1322 ]]
        return "http://www.roblox.com/asset/?id=4780426469";
    end,
    ["get_iconhd_trophy"] = function(_) --[[ Name: get_iconhd_trophy ]] --[[ Line: 1324 ]]
        return "rbxassetid://5384698400";
    end,
    ["get_iconhd_shop"] = function(_) --[[ Name: get_iconhd_shop ]] --[[ Line: 1325 ]]
        return "rbxassetid://5384698039";
    end,
    ["get_iconhd_song"] = function(_) --[[ Name: get_iconhd_song ]] --[[ Line: 1326 ]]
        return "rbxassetid://5384698174";
    end,
    ["get_iconhd_crafting"] = function(_) --[[ Name: get_iconhd_crafting ]] --[[ Line: 1327 ]]
        return "rbxassetid://5384698548";
    end,
    ["get_iconhd_vip"] = function(_) --[[ Name: get_iconhd_vip ]] --[[ Line: 1328 ]]
        return "rbxassetid://5384697907";
    end,
    ["get_iconhd_mission"] = function(_) --[[ Name: get_iconhd_mission ]] --[[ Line: 1329 ]]
        return "rbxassetid://5384698273";
    end,
    ["get_hitword_miss_assetid"] = function(_) --[[ Name: get_hitword_miss_assetid ]] --[[ Line: 1331 ]]
        return "rbxassetid://698514044";
    end,
    ["get_hitword_okay_assetid"] = function(_) --[[ Name: get_hitword_okay_assetid ]] --[[ Line: 1332 ]]
        return "rbxassetid://698514143";
    end,
    ["get_hitword_great_assetid"] = function(_) --[[ Name: get_hitword_great_assetid ]] --[[ Line: 1333 ]]
        return "rbxassetid://698514147";
    end,
    ["get_hitword_perfect_assetid"] = function(_) --[[ Name: get_hitword_perfect_assetid ]] --[[ Line: 1334 ]]
        return "rbxassetid://698514146";
    end,
    ["get_song_container_assetid"] = function(_) --[[ Name: get_song_container_assetid ]] --[[ Line: 1336 ]]
        return "rbxassetid://4937046140";
    end,
    ["get_song_container_selected_assetid"] = function(_) --[[ Name: get_song_container_selected_assetid ]] --[[ Line: 1337 ]]
        return "rbxassetid://4937046209";
    end,
    ["get_news_pageitem_selected_assetid"] = function(_) --[[ Name: get_news_pageitem_selected_assetid ]] --[[ Line: 1339 ]]
        return "rbxassetid://994257885";
    end,
    ["get_news_pageitem_unselected_assetid"] = function(_) --[[ Name: get_news_pageitem_unselected_assetid ]] --[[ Line: 1340 ]]
        return "rbxassetid://994257886";
    end,
    ["get_leaderboard_icon"] = function(_) --[[ Name: get_leaderboard_icon ]] --[[ Line: 1342 ]]
        return "rbxassetid://11470253638";
    end,
    ["get_song_icon"] = function(_) --[[ Name: get_song_icon ]] --[[ Line: 1343 ]]
        return "rbxassetid://5384698174";
    end,
    ["get_team_icon"] = function(_) --[[ Name: get_team_icon ]] --[[ Line: 1344 ]]
        return "rbxassetid://11470261198";
    end,
    ["get_tab_selected_container_assetid"] = function(_) --[[ Name: get_tab_selected_container_assetid ]] --[[ Line: 1346 ]]
        return "rbxassetid://4826777206";
    end,
    ["get_tab_selected_container_noarrow_assetid"] = function(_) --[[ Name: get_tab_selected_container_noarrow_assetid ]] --[[ Line: 1347 ]]
        return "rbxassetid://10529352007";
    end,
    ["get_tab_unselected_container_assetid"] = function(_) --[[ Name: get_tab_unselected_container_assetid ]] --[[ Line: 1348 ]]
        return "rbxassetid://4831319704";
    end,
    ["get_leaderboard_bubble_gold_assetid"] = function(_) --[[ Name: get_leaderboard_bubble_gold_assetid ]] --[[ Line: 1350 ]]
        return "rbxassetid://2038324216";
    end,
    ["get_leaderboard_bubble_silver_assetid"] = function(_) --[[ Name: get_leaderboard_bubble_silver_assetid ]] --[[ Line: 1351 ]]
        return "rbxassetid://2038324215";
    end,
    ["get_leaderboard_bubble_bronze_assetid"] = function(_) --[[ Name: get_leaderboard_bubble_bronze_assetid ]] --[[ Line: 1352 ]]
        return "rbxassetid://2038324214";
    end,
    ["get_leaderboard_bubble_none_assetid"] = function(_) --[[ Name: get_leaderboard_bubble_none_assetid ]] --[[ Line: 1353 ]]
        return "rbxassetid://2038324213";
    end,
    ["get_icon_box_open_assetid"] = function(_) --[[ Name: get_icon_box_open_assetid ]] --[[ Line: 1355 ]]
        return "rbxassetid://9098000789";
    end,
    ["get_icon_box_closed_assetid"] = function(_) --[[ Name: get_icon_box_closed_assetid ]] --[[ Line: 1356 ]]
        return "rbxassetid://9098000928";
    end,
    ["get_challengepass_item_assetid"] = function(_) --[[ Name: get_challengepass_item_assetid ]] --[[ Line: 1358 ]]
        return "rbxassetid://4150360667";
    end,
    ["get_challengepass_item_selected_assetid"] = function(_) --[[ Name: get_challengepass_item_selected_assetid ]] --[[ Line: 1359 ]]
        return "rbxassetid://4150360560";
    end,
    ["get_coinstack_large_assetid"] = function(_) --[[ Name: get_coinstack_large_assetid ]] --[[ Line: 1361 ]]
        return "rbxassetid://994257887";
    end,
    ["get_starstack_large_assetid"] = function(_) --[[ Name: get_starstack_large_assetid ]] --[[ Line: 1362 ]]
        return "rbxassetid://994258672";
    end,
    ["get_inventory_item_assetid"] = function(_) --[[ Name: get_inventory_item_assetid ]] --[[ Line: 1364 ]]
        return "rbxassetid://752934529";
    end,
    ["get_inventory_item_selected_assetid"] = function(_) --[[ Name: get_inventory_item_selected_assetid ]] --[[ Line: 1365 ]]
        return "rbxassetid://837294128";
    end,
    ["get_spinner_assetid"] = function(_) --[[ Name: get_spinner_assetid ]] --[[ Line: 1367 ]]
        return "rbxassetid://950300586";
    end,
    ["get_miniqueue_ready_assetid"] = function(_) --[[ Name: get_miniqueue_ready_assetid ]] --[[ Line: 1368 ]]
        return "rbxassetid://792144537";
    end,
    ["get_mission_box_assetid"] = function(_) --[[ Name: get_mission_box_assetid ]] --[[ Line: 1370 ]]
        return "rbxassetid://1143055487";
    end,
    ["get_mission_box_weekly_assetid"] = function(_) --[[ Name: get_mission_box_weekly_assetid ]] --[[ Line: 1371 ]]
        return "rbxassetid://2640160108";
    end,
    ["get_play_options_song_container_assetid"] = function(_) --[[ Name: get_play_options_song_container_assetid ]] --[[ Line: 1373 ]]
        return "rbxassetid://4937046140";
    end,
    ["get_play_options_song_container_selected_assetid"] = function(_) --[[ Name: get_play_options_song_container_selected_assetid ]] --[[ Line: 1374 ]]
        return "rbxassetid://4937046209";
    end,
    ["get_favorite_icon"] = function(_) --[[ Name: get_favorite_icon ]] --[[ Line: 1376 ]]
        return "rbxassetid://8455858272";
    end,
    ["get_unfavorite_icon"] = function(_) --[[ Name: get_unfavorite_icon ]] --[[ Line: 1377 ]]
        return "rbxassetid://8455858160";
    end,
    ["lookat_matrix"] = function(_, p170, p171) --[[ Name: lookat_matrix ]] --[[ Line: 1379 ]]
        local l_Unit_0 = (p171 - p170).Unit
        local v172 = l_Unit_0:Cross(Vector3.new(0, 1, 0))
        return CFrame.fromMatrix(p170, v172, (v172:Cross(l_Unit_0)));
    end,
    ["player_id_online"] = function(_, p173) --[[ Name: player_id_online ]] --[[ Line: 1483 ]]
        --[[ Upvalues: (copy 1): s_Players_0 ]]
        local v174 = false
        for _, v175 in pairs(s_Players_0:GetPlayers()) do
            if v175.UserId == p173 then
                return true;
            end;
        end;
        return v174;
    end,
    ["get_player_id"] = function(_, p176) --[[ Name: get_player_id ]] --[[ Line: 1494 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        local l_UserId_0 = p176.UserId
        if v_u_11.DoDebugLoadPlayerRbxId == true then
            l_UserId_0 = v_u_11.DebugLoadPlayerRbxId
        end;
        return l_UserId_0;
    end,
    ["large_number"] = function(_) --[[ Name: large_number ]] --[[ Line: 1564 ]]
        return 1000000000;
    end,
    ["input_max_number"] = function(_) --[[ Name: input_max_number ]] --[[ Line: 1570 ]]
        return 1000000;
    end,
    ["is_prod_build"] = function(_) --[[ Name: is_prod_build ]] --[[ Line: 1585 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:is_prod_build();
    end,
    ["is_dev_build"] = function(_) --[[ Name: is_dev_build ]] --[[ Line: 1586 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:is_dev_build();
    end
}
v_u_177.dir_ang_deg = function(_, p178, p179) --[[ Name: dir_ang_deg ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    return v_u_177:rad_to_deg((math.atan2(p179, p178)));
end;
v_u_177.ang_deg_dir = function(_, p180) --[[ Name: ang_deg_dir ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v181 = v_u_177:deg_to_rad(p180)
    return Vector2.new(math.cos(v181), (math.sin(v181)));
end;
v_u_177.table_to_str = function(_, p182) --[[ Name: table_to_str ]] --[[ Line: 80 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    return v_u_177:table_to_string(p182);
end;
v_u_177.tab_to_str = function(_, p183) --[[ Name: tab_to_str ]] --[[ Line: 81 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    return v_u_177:table_to_string(p183);
end;
local v_u_184 = v_u_2.mwc(tick() % 1000)
local v_u_185 = false
v_u_177.is_mobile = function(_) --[[ Name: is_mobile ]] --[[ Line: 91 ]]
    --[[ Upvalues: (ref 1): v_u_185 ]]
    return v_u_185;
end;
local v_u_186 = nil
local function _() --[[ Name: get_camera ]] --[[ Line: 97 ]]
    --[[ Upvalues: (ref 1): v_u_186 ]]
    return v_u_186;
end;
v_u_177.get_camera = function(_) --[[ Name: get_camera ]] --[[ Line: 100 ]]
    --[[ Upvalues: (ref 1): v_u_186 ]]
    return v_u_186;
end;
local v_u_187 = CFrame.new()
local v_u_188 = v8.new()
local v_u_189 = CFrame.new()
local v_u_190 = nil
local v_u_191 = nil
local v_u_192 = nil
local v_u_193 = nil
local v_u_194 = nil
local v_u_195 = nil
local v_u_196 = v_u_4:new()
local v_u_197 = false
local v_u_198 = v_u_4:new()
v_u_177.get_name_to_player = function(_) --[[ Name: get_name_to_player ]] --[[ Line: 119 ]]
    --[[ Upvalues: (copy 1): v_u_196 ]]
    return v_u_196;
end;
v_u_177.get_lowercase_name_to_player = function(_) --[[ Name: get_lowercase_name_to_player ]] --[[ Line: 120 ]]
    --[[ Upvalues: (ref 1): v_u_197, (copy 2): v_u_198, (copy 3): v_u_196 ]]
    if v_u_197 == false then
        v_u_197 = true
        v_u_198:clear()
        for v199, v200 in v_u_196:key_itr() do
            v_u_198:add(string.lower(v199), v200)
        end;
    end;
    return v_u_198;
end;
local v_u_201 = 36
v_u_177.topbar_size = function(_) --[[ Name: topbar_size ]] --[[ Line: 134 ]]
    --[[ Upvalues: (ref 1): v_u_201 ]]
    return v_u_201;
end;
local v_u_202 = nil
local function f_verify_sputil_screengui() --[[ Name: verify_sputil_screengui ]] --[[ Line: 137 ]]
    --[[ Upvalues: (ref 1): v_u_202, (copy 2): s_Players_0 ]]
    if v_u_202 ~= nil then
        return true;
    end;
    if s_Players_0.LocalPlayer == nil then
        return false;
    end;
    if s_Players_0.LocalPlayer:FindFirstChild("PlayerGui") == nil then
        return false;
    end;
    if s_Players_0.LocalPlayer.PlayerGui:FindFirstChild("SPUtil_test") == nil then
        v_u_202 = Instance.new("ScreenGui", s_Players_0.LocalPlayer.PlayerGui)
        v_u_202.Name = "SPUtil_test"
        v_u_202.ResetOnSpawn = false
    end;
    return true;
end;
local v_u_203 = Vector2.new(0, 0)
local v_u_204 = Vector2.new()
v_u_177.screen_size = function(_) --[[ Name: screen_size ]] --[[ Line: 156 ]]
    --[[ Upvalues: (copy 1): f_verify_sputil_screengui, (ref 2): v_u_203, (ref 3): v_u_202, (ref 4): v_u_204, (copy 5): v_u_177 ]]
    if f_verify_sputil_screengui() == false then
        return v_u_203;
    end;
    local l_AbsoluteSize_0 = v_u_202.AbsoluteSize
    if v_u_204 ~= l_AbsoluteSize_0 then
        v_u_204 = l_AbsoluteSize_0
        v_u_203 = Vector2.new(l_AbsoluteSize_0.X + 0, l_AbsoluteSize_0.Y + v_u_177:topbar_size())
    end;
    return v_u_203;
end;
v_u_177.update = function(_) --[[ Name: update ]] --[[ Line: 168 ]]
    --[[ Upvalues: (ref 1): v_u_186, (ref 2): v_u_190, (ref 3): v_u_193, (ref 4): v_u_194, (ref 5): v_u_195, (copy 6): s_Players_0, (ref 7): v_u_191, (ref 8): v_u_192, (ref 9): v_u_187, (copy 10): v_u_188, (copy 11): v_u_177, (ref 12): v_u_189, (ref 13): v_u_185, (copy 14): s_UserInputService_0, (copy 15): v_u_196, (ref 16): v_u_197, (copy 17): v_u_198, (ref 18): v_u_201, (ref 19): v_u_204 ]]
    v_u_186 = game.Workspace.Camera
    v_u_190 = nil
    v_u_193 = nil
    v_u_194 = nil
    v_u_195 = nil
    v_u_190 = game and (s_Players_0 and s_Players_0.LocalPlayer)
    if v_u_190 then
        v_u_191 = v_u_190.UserId
        v_u_192 = v_u_190.Name
        v_u_193 = v_u_190.Character
        v_u_194 = v_u_193 and v_u_193:FindFirstChild("Humanoid")
        if v_u_194 then
            v_u_195 = v_u_194.RootPart
        end;
    end;
    if v_u_186 then
        v_u_187 = v_u_186.CFrame
        v_u_188:from_cframe(v_u_187)
    end;
    local _, v205 = v_u_177:get_local_character_humanoid_rootpart()
    if v205 ~= nil then
        v_u_189 = v205.CFrame
    end;
    v_u_185 = s_UserInputService_0.TouchEnabled
    v_u_196:clear()
    v_u_197 = false
    v_u_198:clear()
    for _, v206 in pairs(game.Players:GetPlayers()) do
        v_u_196:add(v206.Name, v206)
    end;
    local v207, _ = game:GetService("GuiService"):GetGuiInset()
    v_u_201 = v207.Y
    v_u_204 = Vector2.new()
end;
v_u_177.get_local_character = function(_) --[[ Name: get_local_character ]] --[[ Line: 218 ]]
    --[[ Upvalues: (ref 1): v_u_193 ]]
    return v_u_193;
end;
v_u_177.get_local_character_humanoid_rootpart = function(_) --[[ Name: get_local_character_humanoid_rootpart ]] --[[ Line: 222 ]]
    --[[ Upvalues: (ref 1): v_u_194, (ref 2): v_u_195 ]]
    return v_u_194, v_u_195;
end;
v_u_177.get_camera_cframe_uncached = function(_) --[[ Name: get_camera_cframe_uncached ]] --[[ Line: 226 ]]
    --[[ Upvalues: (ref 1): v_u_186 ]]
    return v_u_186.CFrame;
end;
v_u_177.get_camera_cframe = function(_) --[[ Name: get_camera_cframe ]] --[[ Line: 230 ]]
    --[[ Upvalues: (ref 1): v_u_187 ]]
    return v_u_187;
end;
v_u_177.get_camera_cframe_lv = function(_) --[[ Name: get_camera_cframe_lv ]] --[[ Line: 234 ]]
    --[[ Upvalues: (copy 1): v_u_188 ]]
    return v_u_188;
end;
v_u_177.get_localplayer_cframe = function(_) --[[ Name: get_localplayer_cframe ]] --[[ Line: 238 ]]
    --[[ Upvalues: (ref 1): v_u_189 ]]
    return v_u_189;
end;
v_u_177.get_local_player = function(_) --[[ Name: get_local_player ]] --[[ Line: 242 ]]
    --[[ Upvalues: (ref 1): v_u_190 ]]
    return v_u_190;
end;
v_u_177.get_local_userid = function(_) --[[ Name: get_local_userid ]] --[[ Line: 244 ]]
    --[[ Upvalues: (ref 1): v_u_191 ]]
    return v_u_191 == nil and -1 or v_u_191;
end;
v_u_177.get_local_username = function(_) --[[ Name: get_local_username ]] --[[ Line: 251 ]]
    --[[ Upvalues: (ref 1): v_u_190 ]]
    return v_u_190 == nil and "?" or v_u_190.Name;
end;
v_u_177.rand_rangef = function(_, p208, p209) --[[ Name: rand_rangef ]] --[[ Line: 258 ]]
    --[[ Upvalues: (copy 1): v_u_184 ]]
    return v_u_184:rand_rangef(p208, p209);
end;
v_u_177.rand_rangei = function(_, p210, p211) --[[ Name: rand_rangei ]] --[[ Line: 262 ]]
    --[[ Upvalues: (copy 1): v_u_184 ]]
    return v_u_184:rand_rangei(p210, p211);
end;
v_u_177.plane_intersect = function(_, p212, p213, p214, p215) --[[ Name: plane_intersect ]] --[[ Line: 293 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v216 = v_u_177:dot(p215, p213)
    if math.abs(v216) > 0 then
        local v217 = v_u_177:dot(p214 - p212, p215) / v216
        if v217 >= 0 then
            return true, p212 + p213 * v217;
        else
            return false, Vector3.new();
        end;
    else
        return false, Vector3.new();
    end;
end;
v_u_177.nxy_to_nontopbar_screen_pos = function(_, p218, p219) --[[ Name: nxy_to_nontopbar_screen_pos ]] --[[ Line: 387 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v220 = v_u_177:screen_size()
    return v220.X * p218, v220.Y * p219 - v_u_177:topbar_size();
end;
v_u_177.nontopbar_screen_pos_to_nxy = function(_, p221, p222) --[[ Name: nontopbar_screen_pos_to_nxy ]] --[[ Line: 394 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v223 = v_u_177:screen_size()
    return p221 / v223.X, (p222 + v_u_177:topbar_size()) / v223.Y;
end;
v_u_177.pos_to_nxy = function(_, p224) --[[ Name: pos_to_nxy ]] --[[ Line: 399 ]]
    --[[ Upvalues: (ref 1): v_u_186, (copy 2): v_u_177 ]]
    local v225, _ = v_u_186:WorldToScreenPoint(p224)
    local v226, v227 = v_u_177:nontopbar_screen_pos_to_nxy(v225.X, v225.Y)
    return Vector2.new(v226, v227);
end;
local v_u_238 = {
    ["TextLabel"] = function(p228, _, p229, _, _) --[[ Line: 409 ]]
        p228.TextTransparency = p229
        if p228.TextStrokeColor3 ~= Color3.new() then
            p228.TextStrokeTransparency = p229
        end;
    end,
    ["TextBox"] = function(p230, _, p231, _, _) --[[ Line: 415 ]]
        p230.TextTransparency = p231
        p230.TextStrokeTransparency = p231
    end,
    ["ImageLabel"] = function(p232, p233, _, p234, p235) --[[ Line: 419 ]]
        p232.ImageTransparency = p234
        if typeof(p235) ~= "table" or p235.NoAlphaHandlerSpecialCases ~= true then
            if #p232.Image == 0 then
                p232.BackgroundTransparency = p233
            end;
        end;
    end,
    ["UIStroke"] = function(p236, _, p237, _, _) --[[ Line: 429 ]]
        p236.Transparency = p237
    end
}
local function f__r_set_alpha_perform(p239, p240, p241) --[[ Name: _r_set_alpha_perform ]] --[[ Line: 433 ]]
    --[[ Upvalues: (copy 1): v_u_177, (copy 2): v_u_238 ]]
    local l_Name_0 = p239.Name
    local v242, v243
    if (p241 == nil or p241.SkipNameCheck ~= true) == true and string.sub(l_Name_0, 1, 1) == "{" then
        local v244 = string.sub(l_Name_0, 1, string.find(l_Name_0, "}"))
        v242 = p240
        v243 = v242
        local v245 = v242
        v242 = v243
        v245 = v243
        local v246 = 1
        while true do
            local v247 = v246 + 1
            local v248 = string.find(v244, "=", v247)
            local v249 = string.find(v244, ",", v247)
            v246 = string.find(v244, "}", v247)
            if v248 == nil or v246 == nil then
                break;
            end;
            local v250 = string.sub(l_Name_0, v247, v248 - 1)
            local v251
            if v249 == nil then
                v251 = string.sub(l_Name_0, v248 + 1, v246 - 1)
            else
                v251 = string.sub(l_Name_0, v248 + 1, v249 - 1)
                v246 = v249
            end;
            if v250 == "BackgroundAlpha" then
                p240 = v_u_177:tra(tonumber(v251) * v_u_177:tra(p240))
            elseif v250 == "TextAlpha" then
                v243 = v_u_177:tra(tonumber(v251) * v_u_177:tra(v243))
            elseif v250 == "ImageAlpha" then
                v242 = v_u_177:tra(tonumber(v251) * v_u_177:tra(v242))
            end;
        end;
    else
        v242 = p240
        v243 = v242
        local v252 = v242
        v242 = v243
        v252 = v243
    end;
    if p241 ~= nil and p241.CheckAttributes == true then
        for v253, _ in pairs(p239:GetAttributes()) do
            if string.sub(v253, 1, 5) == "Alpha" then
                local v254 = p239:GetAttribute(v253)
                if typeof(v254) == "number" then
                    p240 = v_u_177:tra(v_u_177:tra(p240) * v254)
                    v243 = v_u_177:tra(v_u_177:tra(v243) * v254)
                    v242 = v_u_177:tra(v_u_177:tra(v242) * v254)
                end;
            end;
        end;
    end;
    local v255 = v_u_238[p239.ClassName]
    if v255 == nil then
        return false;
    end;
    v255(p239, p240, v243, v242, p241)
    return true;
end;
local function f__r_set_alpha(p256, p257, p258, p259, p260) --[[ Name: _r_set_alpha ]] --[[ Line: 504 ]]
    --[[ Upvalues: (copy 1): f__r_set_alpha_perform, (copy 2): f__r_set_alpha ]]
    if p258 ~= nil then
        for v261 = 1, p258:count() do
            if p256.Name == p258:get(v261) then
                return;
            end;
        end;
    end;
    if not p260 or (p260.CheckAttributes ~= true or p256:GetAttribute("R_SET_ALPHA_V2_NOTRAVERSE_FLAG") ~= true) then
        if p259 ~= nil and f__r_set_alpha_perform(p256, p257, p260) == true then
            p259[#p259 + 1] = p256
        end;
        for _, v262 in pairs(p256:GetChildren()) do
            f__r_set_alpha(v262, p257, p258, p259, p260)
        end;
    end;
end;
v_u_177.r_set_alpha_generate_name = function(_, p263, p264) --[[ Name: r_set_alpha_generate_name ]] --[[ Line: 530 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v265 = "{"
    for v266, v267 in pairs(p263) do
        if v266 == "BackgroundAlpha" or (v266 == "ImageAlpha" or v266 == "TextAlpha") then
            v265 = v265 .. v266 .. "=" .. tostring(v267) .. ","
        else
            v_u_177:errf("r_set_alpha_generate_name unknown key(%s)", v266)
        end;
    end;
    local v268 = v265 .. "}"
    if typeof(p264) == "string" then
        return v268 .. p264;
    else
        local l_Name_1 = p264.Name
        local v269 = string.find(l_Name_1, "}")
        if v269 == nil then
            return v268 .. l_Name_1;
        else
            return v268 .. string.sub(l_Name_1, v269 + 1);
        end;
    end;
end;
local v_u_270 = {}
v_u_177.r_set_alpha = function(_, p271, p272, p273, p274) --[[ Name: r_set_alpha ]] --[[ Line: 558 ]]
    --[[ Upvalues: (copy 1): v_u_177, (copy 2): v_u_270, (copy 3): f__r_set_alpha_perform, (copy 4): f__r_set_alpha ]]
    v_u_177:profilebegin("r_set_alpha")
    local v275 = v_u_177:tra(p272)
    local v276 = v_u_270[p271.Name]
    if v276 == nil or (v276.Root ~= p271 or tick() - v276.Time >= 1) then
        local v277 = {}
        f__r_set_alpha(p271, v275, p273, v277, p274)
        v_u_270[p271.Name] = {
            ["Time"] = tick(),
            ["CacheList"] = v277,
            ["Root"] = p271
        }
    else
        local l_CacheList_0 = v276.CacheList
        for v278 = 1, #l_CacheList_0 do
            f__r_set_alpha_perform(l_CacheList_0[v278], v275, p274)
        end;
    end;
    v_u_177:profileend()
    return p271;
end;
v_u_177.list_set_alpha_name = function(_, p279, p280) --[[ Name: list_set_alpha_name ]] --[[ Line: 581 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    for v281 = 1, p279:count() do
        local v282 = p279:get(v281)
        v282.Name = v_u_177:r_set_alpha_generate_name(p280, v282)
    end;
end;
v_u_177.obj_set_alpha = function(_, p283, p284, p285, p286) --[[ Name: obj_set_alpha ]] --[[ Line: 589 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    v_u_177:list_set_alpha_name(v_u_177:get_list_of_children_of_classname(p283, "TextLabel"), {
        ["TextAlpha"] = p284
    })
    v_u_177:list_set_alpha_name(v_u_177:get_list_of_children_of_classname(p283, "ImageLabel"), {
        ["ImageAlpha"] = p284
    })
    v_u_177:r_set_alpha(p283, p285, nil, p286)
end;
v_u_177.list_apply_suffix_alpha_attribute = function(_, p287, p288, p289) --[[ Name: list_apply_suffix_alpha_attribute ]] --[[ Line: 603 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    for v290 = 1, p287:count() do
        v_u_177:obj_apply_suffix_alpha_attribute(p287:get(v290), p288, p289)
    end;
end;
v_u_177.obj_write_suffix_alpha_attribute_and_apply_all = function(_, p291, p292, p293, p294) --[[ Name: obj_write_suffix_alpha_attribute_and_apply_all ]] --[[ Line: 609 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    v_u_177:list_apply_suffix_alpha_attribute(v_u_177:get_list_of_children_of_classname(p291, "TextLabel"), p292, p293)
    v_u_177:list_apply_suffix_alpha_attribute(v_u_177:get_list_of_children_of_classname(p291, "ImageLabel"), p292, p293)
    v_u_177:r_set_alpha(p291, p294, nil, v_u_177:r_set_alpha_v2_params())
end;
local v_u_295 = {
    ["SkipNameCheck"] = false,
    ["CheckAttributes"] = true
}
v_u_177.r_set_alpha_v2compat_params = function(_) --[[ Name: r_set_alpha_v2compat_params ]] --[[ Line: 619 ]]
    --[[ Upvalues: (copy 1): v_u_295 ]]
    return v_u_295;
end;
local v_u_296 = {
    ["SkipNameCheck"] = true,
    ["CheckAttributes"] = true,
    ["NoAlphaHandlerSpecialCases"] = true
}
v_u_177.r_set_alpha_v2_params = function(_) --[[ Name: r_set_alpha_v2_params ]] --[[ Line: 630 ]]
    --[[ Upvalues: (copy 1): v_u_296 ]]
    return v_u_296;
end;
v_u_177.r_set_alpha_v2 = function(_, p297, p298, p299) --[[ Name: r_set_alpha_v2 ]] --[[ Line: 631 ]]
    --[[ Upvalues: (copy 1): v_u_177, (copy 2): v_u_296 ]]
    v_u_177:r_set_alpha(p297, p298, p299, v_u_296)
end;
v_u_177.profilebegin = function(_, p300) --[[ Name: profilebegin ]] --[[ Line: 641 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    if v_u_177.do_profile == true then
        debug.profilebegin(p300)
    end;
end;
v_u_177.profileend = function(_) --[[ Name: profileend ]] --[[ Line: 646 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    if v_u_177.do_profile == true then
        debug.profileend()
    end;
end;
local v_u_301 = v_u_4:new():add_set_from_table_list({ 103972519, 4631531021 })
v_u_177.is_debug_user = function(_) --[[ Name: is_debug_user ]] --[[ Line: 656 ]]
    --[[ Upvalues: (copy 1): v_u_177, (copy 2): s_Players_0, (copy 3): v_u_301 ]]
    if v_u_177:is_dev_build() then
        return true;
    end;
    if v_u_177.do_profile == true then
        return false;
    end;
    local v_u_302 = false
    v_u_177:ptry(function() --[[ Line: 665 ]]
        --[[ Upvalues: (ref 1): s_Players_0, (ref 2): v_u_301, (ref 3): v_u_302 ]]
        if v_u_301:contains(s_Players_0.LocalPlayer.UserId) then
            v_u_302 = true
        end;
    end)
    return v_u_302;
end;
v_u_177.set_size = function(_, p303, p304, p305, p306) --[[ Name: set_size ]] --[[ Line: 683 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local l_Size_0 = p303.Size
    local v307 = p304 < 0.05 and 0.05 or p304
    local v308 = p305 < 0.05 and 0.05 or p305
    local v309 = p306 < 0.05 and 0.05 or p306
    if v_u_177:flt_cmp_delta(v307, l_Size_0.X, 0.1) == true and (v_u_177:flt_cmp_delta(v308, l_Size_0.Y, 0.1) == true and v_u_177:flt_cmp_delta(v309, l_Size_0.Z, 0.1) == true) then
        return false;
    end;
    p303.Size = Vector3.new(v307, v308, v309)
    return true;
end;
v_u_177.angles = function(_, p310, p311, p312) --[[ Name: angles ]] --[[ Line: 697 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    return CFrame.Angles(v_u_177:deg_to_rad(p310), v_u_177:deg_to_rad(p311), v_u_177:deg_to_rad(p312));
end;
v_u_177.angles_vec3 = function(_, p313) --[[ Name: angles_vec3 ]] --[[ Line: 701 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    return v_u_177:angles(p313.X, p313.Y, p313.Z);
end;
v_u_177.angles_lv = function(_, p314, p315, p316, p317) --[[ Name: angles_lv ]] --[[ Line: 705 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    return p314:set_angles(v_u_177:deg_to_rad(p315), v_u_177:deg_to_rad(p316), v_u_177:deg_to_rad(p317));
end;
v_u_177.angles_vec3_lv = function(_, p318, p319) --[[ Name: angles_vec3_lv ]] --[[ Line: 709 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    return v_u_177:angles_lv(p318, p319.X, p319.Y, p319.Z);
end;
local v_u_320 = v_u_4:new({
    [v_u_10.NoteResult_Miss] = "Miss",
    [v_u_10.NoteResult_Okay] = "Okay",
    [v_u_10.NoteResult_Great] = "Great",
    [v_u_10.NoteResult_Perfect] = "Perfect"
})
v_u_177.noteresult_to_string = function(_, p321) --[[ Name: noteresult_to_string ]] --[[ Line: 767 ]]
    --[[ Upvalues: (copy 1): v_u_320 ]]
    return v_u_320:get(p321);
end;
v_u_177.timedelta_to_result_obj = function(_, p322, p323) --[[ Name: timedelta_to_result_obj ]] --[[ Line: 771 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    return v_u_177:timedelta_to_result(p322, p323[1], p323[2], p323[3], p323[4], p323[5], p323[6]);
end;
local v_u_324 = v_u_4:new()
v_u_177.get_user_thumbnail = function(_, p_u_325, p_u_326, p_u_327, p_u_328, p_u_329) --[[ Name: get_user_thumbnail ]] --[[ Line: 776 ]]
    --[[ Upvalues: (copy 1): v_u_324, (copy 2): v_u_177, (copy 3): s_Players_0 ]]
    if p_u_328 == nil then
        p_u_328 = Enum.ThumbnailType.HeadShot
    end;
    if p_u_329 == nil then
        p_u_329 = Enum.ThumbnailSize.Size180x180
    end;
    local v_u_330 = string.format("%s_%s_%s", tostring(p_u_328), tostring(p_u_329), (tostring(p_u_325)))
    if v_u_324:contains(v_u_330) then
        p_u_326(v_u_324:get(v_u_330), true)
    elseif p_u_328 == Enum.ThumbnailType.HeadShot and p_u_329 == Enum.ThumbnailSize.Size180x180 then
        local v331 = string.format("rbxthumb://type=AvatarHeadShot&id=%s&w=180&h=180", (tostring(p_u_325)))
        v_u_324:add(v_u_330, v331)
        p_u_326(v331, true)
    elseif p_u_328 == Enum.ThumbnailType.AvatarThumbnail and p_u_329 == Enum.ThumbnailSize.Size180x180 then
        local v332 = string.format("rbxthumb://type=Avatar&id=%s&w=180&h=180", (tostring(p_u_325)))
        v_u_324:add(v_u_330, v332)
        p_u_326(v332, true)
    else
        v_u_177:spawn(function() --[[ Line: 805 ]]
            --[[ Upvalues: (ref 1): s_Players_0, (copy 2): p_u_325, (ref 3): p_u_328, (ref 4): p_u_329, (copy 5): p_u_327, (ref 6): v_u_324, (copy 7): v_u_330, (copy 8): p_u_326, (ref 9): v_u_177 ]]
            while true do
                local v333, v334 = s_Players_0:GetUserThumbnailAsync(p_u_325, p_u_328, p_u_329)
                if v334 == true or p_u_327 ~= true then
                    break;
                end;
                v_u_177:thread_sleep(0.25)
            end;
            v_u_324:add(v_u_330, v333)
            p_u_326(v333, v334)
        end)
    end;
end;
local function f_r_get_list_of_children_of_classname(p335, p336, p337) --[[ Name: r_get_list_of_children_of_classname ]] --[[ Line: 819 ]]
    --[[ Upvalues: (copy 1): f_r_get_list_of_children_of_classname ]]
    if p335.ClassName == p336 then
        p337:push_back(p335)
    end;
    for _, v338 in pairs(p335:GetChildren()) do
        f_r_get_list_of_children_of_classname(v338, p336, p337)
    end;
end;
v_u_177.get_list_of_children_of_classname = function(_, p339, p340) --[[ Name: get_list_of_children_of_classname ]] --[[ Line: 828 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): f_r_get_list_of_children_of_classname ]]
    local v341 = v_u_3:new()
    f_r_get_list_of_children_of_classname(p339, p340, v341)
    return v341;
end;
local v_u_342 = v_u_3:new()
v_u_177.first_child_of_type = function(_, p343, p344) --[[ Name: first_child_of_type ]] --[[ Line: 843 ]]
    --[[ Upvalues: (copy 1): v_u_342, (copy 2): v_u_177 ]]
    v_u_342:clear()
    v_u_177:fill_list_of_direct_children_of_classname(p343, p344, v_u_342)
    local v345
    if v_u_342:count() > 0 then
        v345 = v_u_342:get(1)
    else
        v345 = nil
    end;
    v_u_342:clear()
    return v345;
end;
local v_u_346 = v_u_4:new()
v_u_177.obj_has_children_of_names = function(_, p347, p348) --[[ Name: obj_has_children_of_names ]] --[[ Line: 855 ]]
    --[[ Upvalues: (copy 1): v_u_346 ]]
    v_u_346:clear()
    for v349 = 1, #p348 do
        v_u_346:add(p348[v349], false)
    end;
    for _, v350 in pairs(p347:GetChildren()) do
        if v_u_346:contains(v350.Name) then
            v_u_346:add(v350.Name, true)
        end;
    end;
    for _, v351 in v_u_346:key_itr() do
        if v351 == false then
            return false;
        end;
    end;
    return true;
end;
v_u_177.running_avg_collector = function(_) --[[ Name: running_avg_collector ]] --[[ Line: 881 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v352 = {}
    local v_u_353 = 0
    local v_u_354 = 0
    v352.get_avg = function(_) --[[ Name: get_avg ]] --[[ Line: 885 ]]
        --[[ Upvalues: (ref 1): v_u_353 ]]
        return v_u_353;
    end;
    v352.get_ct = function(_) --[[ Name: get_ct ]] --[[ Line: 886 ]]
        --[[ Upvalues: (ref 1): v_u_354 ]]
        return v_u_354;
    end;
    v352.clear = function(_) --[[ Name: clear ]] --[[ Line: 887 ]]
        --[[ Upvalues: (ref 1): v_u_353, (ref 2): v_u_354 ]]
        v_u_353 = 0
        v_u_354 = 0
    end;
    v352.push_val = function(_, p355) --[[ Name: push_val ]] --[[ Line: 891 ]]
        --[[ Upvalues: (ref 1): v_u_354, (ref 2): v_u_353, (ref 3): v_u_177 ]]
        v_u_354 = v_u_354 + 1
        v_u_353 = v_u_177:running_avg(v_u_353, p355, v_u_354)
    end;
    return v352;
end;
local v_u_356 = v_u_4:new()
v_u_177.ptry = function(_, p_u_357, _) --[[ Name: ptry ]] --[[ Line: 910 ]]
    --[[ Upvalues: (copy 1): v_u_177, (copy 2): v_u_356, (copy 3): v_u_7 ]]
    local v358, v359 = v_u_177:try(function() --[[ Line: 912 ]]
        --[[ Upvalues: (copy 1): p_u_357 ]]
        p_u_357()
    end)
    if v358 ~= true then
        local v360 = tostring(v359.Error) .. tostring(v359.StackTrace)
        if v_u_356:contains(v360) == false then
            v_u_356:add_set(v360)
            v_u_7:warnf("SPUtil:ptry(%s)[%s]", v359.Error, v359.StackTrace)
        end;
    end;
    return v358;
end;
local v_u_361 = v_u_3:new()
local v_u_362 = v_u_4:new()
v_u_177.table_checksum = function(_, p363, p364, p365) --[[ Name: table_checksum ]] --[[ Line: 927 ]]
    --[[ Upvalues: (copy 1): v_u_361, (copy 2): v_u_362 ]]
    v_u_361:clear()
    v_u_362:clear()
    for v366, v367 in pairs(p364) do
        local v368 = tostring(v366)
        v_u_361:push_back(v368)
        v_u_362:add(v368, v367)
    end;
    v_u_361:sort(function(p369, p370) --[[ Line: 936 ]]
        return p369 < p370;
    end)
    local v371 = tostring(p365)
    for v372 = 1, v_u_361:count() do
        local v373 = v_u_361:get(v372)
        v371 = v371 .. v373 .. tostring(v_u_362:get(v373))
    end;
    return p363(v371);
end;
local v_u_374 = nil
v_u_177.hash_str = function(_, p375) --[[ Name: hash_str ]] --[[ Line: 948 ]]
    --[[ Upvalues: (ref 1): v_u_374, (copy 2): v_u_177 ]]
    if v_u_374 == nil then
        v_u_374 = v_u_177:hash_creator(8388617)
    end;
    return v_u_374(p375);
end;
local v_u_376 = v_u_3:new()
local v_u_377 = true
v_u_177.gen_name = function(_, p378) --[[ Name: gen_name ]] --[[ Line: 972 ]]
    --[[ Upvalues: (ref 1): v_u_377, (copy 2): v_u_376, (copy 3): v_u_177 ]]
    if v_u_377 == false then
        return p378 .. "_gen_name";
    end;
    if v_u_376:count() >= 30 and math.random() * 100 < 2 then
        v_u_376:pop_back()
    end;
    if v_u_376:count() >= 30 then
        return v_u_376:random();
    end;
    local v379 = ""
    for _ = 1, 10 do
        v379 = v379 .. tostring((string.char(v_u_177:rand_rangei(65, 125))))
    end;
    v_u_376:push_back(v379)
    return v379;
end;
v_u_177.thread_sleep = function(_, p380) --[[ Name: thread_sleep ]] --[[ Line: 994 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    v_u_177:wait(p380)
end;
v_u_177.num_placify = function(_, p381) --[[ Name: num_placify ]] --[[ Line: 1062 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    if p381 % 100 == 11 then
        return v_u_177:comma_value(p381) .. "th";
    elseif p381 % 100 == 12 then
        return v_u_177:comma_value(p381) .. "th";
    elseif p381 % 100 == 13 then
        return v_u_177:comma_value(p381) .. "th";
    elseif p381 % 10 == 0 then
        return v_u_177:comma_value(p381) .. "th";
    elseif p381 % 10 == 1 then
        return v_u_177:comma_value(p381) .. "st";
    elseif p381 % 10 == 2 then
        return v_u_177:comma_value(p381) .. "nd";
    elseif p381 % 10 == 3 then
        return v_u_177:comma_value(p381) .. "rd";
    else
        return v_u_177:comma_value(p381) .. "th";
    end;
end;
local v_u_382 = nil
v_u_177.get_local_mouse = function(_) --[[ Name: get_local_mouse ]] --[[ Line: 1124 ]]
    --[[ Upvalues: (ref 1): v_u_382, (copy 2): s_Players_0 ]]
    if v_u_382 == nil then
        v_u_382 = s_Players_0.LocalPlayer:GetMouse()
    end;
    return v_u_382;
end;
local v_u_383 = Vector2.new()
v_u_177.get_cursor_nxy = function(_) --[[ Name: get_cursor_nxy ]] --[[ Line: 1132 ]]
    --[[ Upvalues: (copy 1): v_u_177, (ref 2): v_u_383 ]]
    local v384 = v_u_177:get_local_mouse()
    if v384 == nil then
        return v_u_383;
    end;
    local v385, v386 = v_u_177:nontopbar_screen_pos_to_nxy(v384.X, v384.Y)
    if v_u_383.X ~= v385 or v_u_383.Y ~= v386 then
        v_u_383 = Vector2.new(v385, v386)
    end;
    return v_u_383;
end;
local v_u_387 = v_u_3:new()
local v_u_388 = v_u_3:new()
v_u_177.push_gc_count = function(_, p389) --[[ Name: push_gc_count ]] --[[ Line: 1196 ]]
    --[[ Upvalues: (copy 1): v_u_387, (copy 2): v_u_388, (copy 3): v_u_177 ]]
    v_u_387:push_back(p389)
    v_u_388:push_back(v_u_177:gc_count())
end;
v_u_177.pop_gc_count = function(_) --[[ Name: pop_gc_count ]] --[[ Line: 1202 ]]
    --[[ Upvalues: (copy 1): v_u_387, (copy 2): v_u_388, (copy 3): v_u_177 ]]
    print(string.format("GC[%s](%d)", tostring((v_u_387:pop_back())), v_u_177:gc_count() - v_u_388:pop_back()))
end;
local v_u_390 = v_u_3:new()
local v_u_391 = v_u_3:new()
v_u_177.push_test_timer = function(_, p392) --[[ Name: push_test_timer ]] --[[ Line: 1217 ]]
    --[[ Upvalues: (copy 1): v_u_390, (copy 2): v_u_391 ]]
    v_u_390:push_back(p392)
    v_u_391:push_back(tick())
end;
v_u_177.pop_test_timer = function(_) --[[ Name: pop_test_timer ]] --[[ Line: 1222 ]]
    --[[ Upvalues: (copy 1): v_u_390, (copy 2): v_u_391 ]]
    print(string.format("Timer[%s](%f)", tostring((v_u_390:pop_back())), tick() - v_u_391:pop_back()))
end;
local v_u_393 = v9:new(0, 0, 0, 0)
v_u_177.get_ui_object_nrect = function(_, p394, p395) --[[ Name: get_ui_object_nrect ]] --[[ Line: 1285 ]]
    --[[ Upvalues: (copy 1): v_u_393, (copy 2): v_u_177 ]]
    if p395 == nil then
        p395 = v_u_393
    end;
    local v396 = v_u_177:screen_size()
    local l_AbsolutePosition_0 = p394.AbsolutePosition
    local l_AbsoluteSize_1 = p394.AbsoluteSize
    local v397 = Vector2.new(l_AbsolutePosition_0.X, l_AbsolutePosition_0.Y + v_u_177:topbar_size())
    local v398 = v397.X / v396.X
    local v399 = v397.Y / v396.Y
    return p395:set(v398, v399, v398 + l_AbsoluteSize_1.X / v396.X, v399 + l_AbsoluteSize_1.Y / v396.Y);
end;
local l_fromAxisAngle_0 = CFrame.fromAxisAngle
local l_components_0 = CFrame.new().components
local l_inverse_0 = CFrame.new().inverse
local l_new_0 = Vector3.new
local l_acos_0 = math.acos
local l_sqrt_0 = math.sqrt
v_u_177.cframe_interpolator = function(_, p_u_400, p401) --[[ Name: cframe_interpolator ]] --[[ Line: 1396 ]]
    --[[ Upvalues: (copy 1): l_components_0, (copy 2): l_inverse_0, (copy 3): l_new_0, (copy 4): l_acos_0, (copy 5): l_sqrt_0, (copy 6): l_fromAxisAngle_0 ]]
    local _, _, _, v402, v403, v404, v405, v406, v407, v408, v409, v410 = l_components_0(l_inverse_0(p_u_400) * p401)
    local v411 = (v402 + v406 + v410 - 1) / 2
    local v_u_412 = l_new_0(v409 - v407, v404 - v408, v405 - v403)
    local v_u_413 = p401.p - p_u_400.p
    if v411 == 0 then
        return 0, function(p414) --[[ Line: 1417 ]]
            --[[ Upvalues: (copy 1): p_u_400, (copy 2): v_u_413 ]]
            return p_u_400 + v_u_413 * p414;
        end;
    end;
    if v411 < 0.999 then
        local v_u_415
        if v411 <= -0.9999 then
            v_u_415 = 3.141592653589793
            local v416 = (v402 + 1) / 2
            local v417 = (v406 + 1) / 2
            local v418 = (v410 + 1) / 2
            if v417 < v416 and v418 < v416 then
                if v416 < 0.0001 then
                    v_u_412 = Vector3.new(0, 0.70710677, 0.70710677)
                else
                    local v419 = l_sqrt_0(v416)
                    v_u_412 = l_new_0(v419, (v405 + v403) / 4 / v419, (v408 + v404) / 4 / v419)
                end;
            elseif v418 < v417 then
                if v417 < 0.0001 then
                    v_u_412 = Vector3.new(0.70710677, 0, 0.70710677)
                else
                    local v420 = l_sqrt_0(v417)
                    v_u_412 = l_new_0((v405 + v403) / 4 / v420, v420, (v409 + v407) / 4 / v420)
                end;
            elseif v418 < 0.0001 then
                v_u_412 = Vector3.new(0.70710677, 0.70710677, 0)
            else
                local v421 = l_sqrt_0(v418)
                v_u_412 = l_new_0((v408 + v404) / 4 / v421, (v409 + v407) / 4 / v421, v421)
            end;
        else
            v_u_415 = l_acos_0(v411)
        end;
        return v_u_415, function(p422) --[[ Line: 1478 ]]
            --[[ Upvalues: (copy 1): p_u_400, (ref 2): l_fromAxisAngle_0, (ref 3): v_u_412, (ref 4): v_u_415, (copy 5): v_u_413 ]]
            return p_u_400 * l_fromAxisAngle_0(v_u_412, v_u_415 * p422) + v_u_413 * p422;
        end;
    end;
    local l_p_1 = p_u_400.p
    local _, _, _, v_u_423, v_u_424, v_u_425, v_u_426, v_u_427, v_u_428, v_u_429, v_u_430, v_u_431 = l_components_0(p_u_400)
    local _, _, _, v_u_432, v_u_433, v_u_434, v_u_435, v_u_436, v_u_437, v_u_438, v_u_439, v_u_440 = l_components_0(p401)
    return l_acos_0(v411), function(p441) --[[ Line: 1431 ]]
        --[[ Upvalues: (copy 1): v_u_423, (copy 2): v_u_432, (copy 3): v_u_424, (copy 4): v_u_433, (copy 5): v_u_425, (copy 6): v_u_434, (copy 7): v_u_426, (copy 8): v_u_435, (copy 9): v_u_427, (copy 10): v_u_436, (copy 11): v_u_428, (copy 12): v_u_437, (copy 13): v_u_429, (copy 14): v_u_438, (copy 15): v_u_430, (copy 16): v_u_439, (copy 17): v_u_431, (copy 18): v_u_440, (copy 19): l_p_1, (copy 20): v_u_413 ]]
        local v442 = 1 - p441
        return CFrame.new(0, 0, 0, v_u_423 * v442 + v_u_432 * p441, v_u_424 * v442 + v_u_433 * p441, v_u_425 * v442 + v_u_434 * p441, v_u_426 * v442 + v_u_435 * p441, v_u_427 * v442 + v_u_436 * p441, v_u_428 * v442 + v_u_437 * p441, v_u_429 * v442 + v_u_438 * p441, v_u_430 * v442 + v_u_439 * p441, v_u_431 * v442 + v_u_440 * p441) + (l_p_1 + v_u_413 * p441);
    end;
end;
v_u_177.get_player_humanoid = function(_, p443) --[[ Name: get_player_humanoid ]] --[[ Line: 1502 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    if p443.Character == nil then
        return nil;
    else
        return v_u_177:get_character_humanoid(p443.Character);
    end;
end;
v_u_177.get_character_humanoid = function(_, p444) --[[ Name: get_character_humanoid ]] --[[ Line: 1507 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v445 = v_u_177:first_child_of_type(p444, "Humanoid")
    if v445 == nil then
        local v446 = v_u_177:get_list_of_children_of_classname(p444, "Humanoid")
        if v446:count() > 0 then
            return v446:get(1);
        else
            return nil;
        end;
    else
        return v445;
    end;
end;
v_u_177.get_player_animator = function(_, p447) --[[ Name: get_player_animator ]] --[[ Line: 1518 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v448 = v_u_177:get_player_humanoid(p447)
    if v448 == nil then
        return nil;
    else
        return v_u_177:first_child_of_type(v448, "Animator");
    end;
end;
v_u_177.r_set_basepart_fn = function(_, p449, p450) --[[ Name: r_set_basepart_fn ]] --[[ Line: 1524 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    if p449:IsA("BasePart") then
        p450(p449)
    end;
    for _, v451 in pairs(p449:GetChildren()) do
        v_u_177:r_set_basepart_fn(v451, p450)
    end;
end;
v_u_177.distance_to_camera = function(_, p452) --[[ Name: distance_to_camera ]] --[[ Line: 1533 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v453 = v_u_177:get_camera_cframe()
    local v454 = p452 - v453.p
    v454:Dot(v453.lookVector)
    return v454.magnitude;
end;
v_u_177.filter_string = function(_, p_u_455, p_u_456, _) --[[ Name: filter_string ]] --[[ Line: 1540 ]]
    --[[ Upvalues: (copy 1): s_TextService_0, (copy 2): v_u_177 ]]
    local v_u_457 = string.rep("#", #p_u_455)
    pcall(function() --[[ Line: 1543 ]]
        --[[ Upvalues: (ref 1): s_TextService_0, (copy 2): p_u_455, (copy 3): p_u_456, (ref 4): v_u_177, (ref 5): v_u_457 ]]
        local v458 = s_TextService_0:FilterStringAsync(p_u_455, p_u_456.UserId, Enum.TextFilterContext.PublicChat)
        if v_u_177:is_dev_build() then
            v_u_177:wait(0.25)
        end;
        v_u_457 = v458:GetNonChatStringForBroadcastAsync()
    end)
    return v_u_457;
end;
v_u_177.get_randomized_character_position = function(_, p459, p460, p461, p462, p463) --[[ Name: get_randomized_character_position ]] --[[ Line: 1572 ]]
    --[[ Upvalues: (copy 1): v_u_177 ]]
    local v464 = p461 == nil and 3 or p461
    local v465 = p462 == nil and 8 or p462
    local v466 = p463 == nil and 1 or p463
    local v467 = p460 - p459
    local l_unit_0 = Vector3.new(v467.x, 0, v467.z).unit
    return p459 + l_unit_0 * v_u_177:rand_rangef(-v464, v464) + l_unit_0:Cross(Vector3.new(0, 1, 0)) * v_u_177:rand_rangef(-v465, v465) + Vector3.new(0, 1, 0) * v466;
end;
if v_u_177:is_dev_build() then
    v_u_177.do_profile = true
    v_u_377 = false
end;
v_u_177.get_character_parts = function(_, p468) --[[ Name: get_character_parts ]] --[[ Line: 1593 ]]
    --[[ Upvalues: (copy 1): v_u_177, (copy 2): v_u_7 ]]
    local v469 = v_u_177:get_character_humanoid(p468)
    local v470 = nil
    local v471
    if v469 == nil then
        v471 = nil
    else
        v471 = v469.RootPart
        if v471 then
            v470 = v_u_177:first_child_of_type(v471, "Attachment")
        end;
    end;
    if v469 == nil or (v471 == nil or v470 == nil) then
        return v_u_7:warnf("SPUtil:get_character_parts humanoid(%s) root_part(%s) rig_root_attachment(%s)", tostring(v469), tostring(v471), (tostring(v470)));
    else
        return v469, v471, v470;
    end;
end;
v_u_177.get_character_part_color = function(_, p472, p473) --[[ Name: get_character_part_color ]] --[[ Line: 1613 ]]
    local v474 = p472:FindFirstChild(p473)
    if v474 == nil then
        return Color3.fromRGB(203, 203, 203);
    else
        return v474.Color;
    end;
end;
v_u_177.round_to_nearest = function(_, p475, p476) --[[ Name: round_to_nearest ]] --[[ Line: 1620 ]]
    local v477 = math.floor(p475)
    return math.floor(v477 - v477 % p476);
end;
v_u_177.round_to_decimal_places = function(_, p478, p479) --[[ Name: round_to_decimal_places ]] --[[ Line: 1626 ]]
    local v480 = 10 ^ p479
    return math.floor(p478 * v480 + 0.5) / v480;
end;
v_u_177.invalid_material_id = function(_) --[[ Name: invalid_material_id ]] --[[ Line: 1631 ]]
    return -1;
end;
v_u_177.if_exists = function(_, p_u_481) --[[ Name: if_exists ]] --[[ Line: 1633 ]]
    --[[ Upvalues: (copy 1): v_u_177, (copy 2): v_u_7 ]]
    local v_u_482 = nil
    local v483, v484 = v_u_177:try(function() --[[ Line: 1635 ]]
        --[[ Upvalues: (ref 1): v_u_482, (copy 2): p_u_481 ]]
        v_u_482 = p_u_481()
    end)
    if v483 ~= true then
        v_u_7:warnf("SPUtil:if_exists failed(%s)", v484.Error)
    end;
    return v_u_482;
end;
local function f_is_console_ui() --[[ Name: is_console_ui ]] --[[ Line: 1644 ]]
    --[[ Upvalues: (copy 1): s_GuiService_0 ]]
    return s_GuiService_0:IsTenFootInterface();
end;
local v_u_485 = true
local v_u_486 = false
v_u_177.query_chat_status = function(_) --[[ Name: query_chat_status ]] --[[ Line: 1648 ]]
    --[[ Upvalues: (ref 1): v_u_485, (copy 2): s_TextChatService_0, (copy 3): v_u_177, (ref 4): v_u_486, (copy 5): v_u_7 ]]
    pcall(function() --[[ Line: 1649 ]]
        --[[ Upvalues: (ref 1): v_u_485, (ref 2): s_TextChatService_0, (ref 3): v_u_177, (ref 4): v_u_486, (ref 5): v_u_7 ]]
        task.spawn(function() --[[ Line: 1650 ]]
            --[[ Upvalues: (ref 1): v_u_485, (ref 2): s_TextChatService_0, (ref 3): v_u_177, (ref 4): v_u_486, (ref 5): v_u_7 ]]
            v_u_485 = s_TextChatService_0:CanUserChatAsync(v_u_177:get_local_userid())
            v_u_486 = true
            if v_u_177:is_dev_build() then
                v_u_7:puts("SPUtil:query_chat_status(%s)", (tostring(v_u_485)))
            end;
        end)
        local v_u_487 = tick()
        task.spawn(function() --[[ Line: 1659 ]]
            --[[ Upvalues: (ref 1): v_u_486, (copy 2): v_u_487, (ref 3): v_u_177, (ref 4): v_u_485, (ref 5): v_u_7 ]]
            while v_u_486 == false do
                if tick() - v_u_487 > 3 then
                    v_u_486 = true
                    if v_u_177:is_dev_build() then
                        v_u_485 = false
                    end;
                    v_u_7:warnf("SPUtil:query_chat_status timeout")
                end;
                wait(0.2)
            end;
        end)
    end)
end;
v_u_177.query_chat_status_finished = function(_) --[[ Name: query_chat_status_finished ]] --[[ Line: 1674 ]]
    --[[ Upvalues: (ref 1): v_u_486 ]]
    return v_u_486;
end;
v_u_177.is_console_ui = function(_) --[[ Name: is_console_ui ]] --[[ Line: 1676 ]]
    --[[ Upvalues: (copy 1): f_is_console_ui ]]
    return f_is_console_ui();
end;
v_u_177.do_disable_chat = function(_) --[[ Name: do_disable_chat ]] --[[ Line: 1677 ]]
    --[[ Upvalues: (ref 1): v_u_485 ]]
    return v_u_485 == false;
end;
local function f_list_find_obj_of_same_name_and_classname(p488, p489) --[[ Name: list_find_obj_of_same_name_and_classname ]] --[[ Line: 1687 ]]
    for v490 = 1, p488:count() do
        local v491 = p488:get(v490)
        if v491 ~= nil and (p489 ~= nil and (v491.Name == p489.Name and v491.ClassName == p489.ClassName)) then
            return v491, v490;
        end;
    end;
    return nil, -1;
end;
local function f_r_remove_all_elements_of_model_not_present_in_source(p492, p493) --[[ Name: r_remove_all_elements_of_model_not_present_in_source ]] --[[ Line: 1698 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): f_list_find_obj_of_same_name_and_classname, (copy 3): f_r_remove_all_elements_of_model_not_present_in_source ]]
    if p492 ~= nil then
        if p493 == nil then
            return p492:Destroy();
        end;
        if typeof(p492) ~= typeof(p493) then
            return p492:Destroy();
        end;
        if p492.ClassName ~= p493.ClassName then
            return p492:Destroy();
        end;
        local v494 = v_u_3:new(p492:GetChildren())
        local v495 = v_u_3:new(p493:GetChildren())
        for v496 = v494:count(), 1, -1 do
            local v497 = v494:get(v496)
            local v498, v499 = f_list_find_obj_of_same_name_and_classname(v495, v497)
            if v498 == nil then
                v497:Destroy()
            else
                v494:remove_at(v496)
                v495:remove_at(v499)
                f_r_remove_all_elements_of_model_not_present_in_source(v497, v498)
            end;
        end;
        for _, v500 in v494:key_itr() do
            v500:Destroy()
        end;
    end;
end;
v_u_177.remove_all_elements_of_model_not_present_in_source = function(_, p501, p502) --[[ Name: remove_all_elements_of_model_not_present_in_source ]] --[[ Line: 1724 ]]
    --[[ Upvalues: (copy 1): f_r_remove_all_elements_of_model_not_present_in_source ]]
    f_r_remove_all_elements_of_model_not_present_in_source(p501, p502)
end;
local l_Folder_0 = Instance.new("Folder", game.ReplicatedStorage)
l_Folder_0.Name = "TrashFolder"
v_u_177.get_trash_folder = function(_) --[[ Name: get_trash_folder ]] --[[ Line: 1732 ]]
    --[[ Upvalues: (copy 1): l_Folder_0 ]]
    return l_Folder_0;
end;
v_u_177.move_to_trash_folder_and_delete = function(_, p503) --[[ Name: move_to_trash_folder_and_delete ]] --[[ Line: 1733 ]]
    --[[ Upvalues: (copy 1): l_Folder_0 ]]
    p503.Parent = l_Folder_0
    p503:Destroy()
end;
v_u_177.flag_all_objects_as_present_in_source = function(_, p504) --[[ Name: flag_all_objects_as_present_in_source ]] --[[ Line: 1739 ]]
    --[[ Upvalues: (copy 1): s_CollectionService_0, (copy 2): v_u_177 ]]
    s_CollectionService_0:AddTag(p504, "PresentInSource")
    for _, v505 in pairs(p504:GetDescendants()) do
        v_u_177:flag_all_objects_as_present_in_source(v505)
    end;
end;
v_u_177.remove_objects_not_present_in_source = function(_, p506) --[[ Name: remove_objects_not_present_in_source ]] --[[ Line: 1746 ]]
    --[[ Upvalues: (copy 1): s_CollectionService_0, (copy 2): v_u_177 ]]
    if p506 ~= nil then
        if s_CollectionService_0:HasTag(p506, "PresentInSource") == false then
            return p506:Destroy();
        end;
        for _, v507 in pairs(p506:GetChildren()) do
            v_u_177:remove_objects_not_present_in_source(v507)
        end;
    end;
end;
v_u_177.is_child_of_parent_set = function(_, p508, p509) --[[ Name: is_child_of_parent_set ]] --[[ Line: 1757 ]]
    while p508 ~= nil do
        if p509:contains(p508) then
            return true;
        end;
        p508 = p508.Parent
    end;
    return false;
end;
v_u_177.for_count = function(_, p510, p_u_511) --[[ Name: for_count ]] --[[ Line: 1768 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v512 = v_u_3:new()
    for v513 = 1, p510 do
        v512:push_back(v513)
    end;
    v_u_3:for_each(v512, function(p514) --[[ Line: 1773 ]]
        --[[ Upvalues: (copy 1): p_u_511 ]]
        p_u_511(p514)
    end)
end;
v_u_177.spawn = function(_, p_u_515) --[[ Name: spawn ]] --[[ Line: 1778 ]]
    task.spawn(function() --[[ Line: 1779 ]]
        --[[ Upvalues: (copy 1): p_u_515 ]]
        if p_u_515 then
            p_u_515()
        end;
    end)
end;
v_u_177.wait = function(_, p516) --[[ Name: wait ]] --[[ Line: 1786 ]]
    task.wait(p516)
end;
v_u_177.request_cache = function(_, p_u_517, p_u_518, p_u_519) --[[ Name: request_cache ]] --[[ Line: 1790 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v520 = {}
    local v_u_521 = 0
    local v_u_522 = v_u_3:new()
    v520.get_cached = function(_, p523) --[[ Name: get_cached ]] --[[ Line: 1800 ]]
        --[[ Upvalues: (ref 1): v_u_521, (copy 2): p_u_517, (ref 3): p_u_518, (copy 4): v_u_522, (copy 5): p_u_519 ]]
        if tick() - v_u_521 < p_u_517 then
            return p523(p_u_518);
        end;
        if v_u_522:count() > 0 then
            return v_u_522:push_back(p523);
        end;
        v_u_522:push_back(p523)
        p_u_519(function(p524) --[[ Line: 1808 ]]
            --[[ Upvalues: (ref 1): v_u_521, (ref 2): p_u_518, (ref 3): v_u_522 ]]
            v_u_521 = tick()
            p_u_518 = p524
            for _, v525 in v_u_522:key_itr() do
                v525(p_u_518)
            end;
            v_u_522:clear()
        end)
    end;
    return v520;
end;
v_u_177.id_to_request_cache = function(_, p_u_526, p_u_527, p_u_528, p_u_529) --[[ Name: id_to_request_cache ]] --[[ Line: 1823 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_177 ]]
    local v530 = {}
    local v_u_531 = v_u_4:new()
    v530.id_get_cached = function(_, p_u_532, p533) --[[ Name: id_get_cached ]] --[[ Line: 1833 ]]
        --[[ Upvalues: (copy 1): p_u_529, (copy 2): v_u_531, (ref 3): v_u_177, (copy 4): p_u_526, (copy 5): p_u_527, (copy 6): p_u_528 ]]
        local v534
        if p_u_529 == nil then
            v534 = p_u_532
        else
            v534 = p_u_529(p_u_532)
        end;
        if v_u_531:contains(v534) ~= true then
            v_u_531:add(v534, v_u_177:request_cache(p_u_526, p_u_527, function(p535) --[[ Line: 1843 ]]
                --[[ Upvalues: (ref 1): p_u_528, (copy 2): p_u_532 ]]
                return p_u_528(p_u_532, p535);
            end))
        end;
        v_u_531:get(v534):get_cached(p533)
    end;
    return v530;
end;
return v_u_177;
