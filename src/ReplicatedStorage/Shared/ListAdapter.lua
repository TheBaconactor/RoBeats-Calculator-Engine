-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v74 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3 ]]
        local v5 = {}
        local v_u_6 = v_u_1:new()
        v5.get_display_elements = function(_) --[[ Name: get_display_elements ]] --[[ Line: 12 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            return v_u_6;
        end;
        local v_u_7 = 0
        local function _(p8, p9) --[[ Line: 16 ]]
            p8:set_visible(p9)
        end;
        local function _(p10) --[[ Line: 17 ]]
            p10:layout()
        end;
        local function v_u_11(_) --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            return v_u_1:new();
        end;
        v5.set_fn_get_data_list = function(p12, p13) --[[ Name: set_fn_get_data_list ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = p13
            return p12;
        end;
        local function v_u_14(_, _, _, _) end;
        v5.set_fn_set_element_data = function(p15, p16) --[[ Name: set_fn_set_element_data ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            v_u_14 = p16
            return p15;
        end;
        local function v_u_17(_, _) end;
        v5.set_fn_next_prev_visible = function(p18, p19) --[[ Name: set_fn_next_prev_visible ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = p19
            return p18;
        end;
        local function v_u_20(_, _) end;
        v5.set_fn_update_page_display = function(p21, p22) --[[ Name: set_fn_update_page_display ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            v_u_20 = p22
            return p21;
        end;
        local function v_u_23(_) end;
        v5.set_fn_is_empty = function(p24, p25) --[[ Name: set_fn_is_empty ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = p25
            return p24;
        end;
        local function v_u_26(_) end;
        v5.set_fn_store_i_offset = function(p27, p28) --[[ Name: set_fn_store_i_offset ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26 = p28
            return p27;
        end;
        v5.get_data_list = function(_) --[[ Name: get_data_list ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11();
        end;
        v5.get_i_offset = function(_) --[[ Name: get_i_offset ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7;
        end;
        v5.set_i_offset = function(p29, p30) --[[ Name: set_i_offset ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7 = p30
            return p29;
        end;
        v5.reset = function(_) --[[ Name: reset ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7 = 0
        end;
        local v_u_31 = false
        v5.set_do_wrap = function(p32, p33) --[[ Name: set_do_wrap ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            v_u_31 = p33
            p32:update_next_prev_visible()
            return p32;
        end;
        v5.next_page = function(p34) --[[ Name: next_page ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            p34:apply_page_offset(v_u_6:count())
        end;
        v5.prev_page = function(p35) --[[ Name: prev_page ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            p35:apply_page_offset(-v_u_6:count())
        end;
        local function _(p36) --[[ Name: get_last_page_i_offset_for_data_list_count ]] --[[ Line: 52 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            if v_u_6:count() == 0 then
                return 0;
            end;
            local v37 = (math.ceil(p36 / v_u_6:count()) - 1) * v_u_6:count()
            return v37 < 0 and 0 or v37;
        end;
        v5.apply_page_offset = function(p38, p39) --[[ Name: apply_page_offset ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_31, (ref 3): v_u_7, (copy 4): v_u_6, (ref 5): v_u_2, (ref 6): v_u_26 ]]
            local v40 = v_u_11():count()
            if v_u_31 then
                if v40 > 0 then
                    v_u_7 = v_u_7 + p39
                    if v_u_7 < 0 then
                        local v41
                        if v_u_6:count() == 0 then
                            v41 = 0
                        else
                            local v42 = (math.ceil(v40 / v_u_6:count()) - 1) * v_u_6:count()
                            v41 = v42 < 0 and 0 or v42
                        end;
                        v_u_7 = v41
                    elseif v40 <= v_u_7 then
                        v_u_7 = 0
                    end;
                else
                    v_u_7 = 0
                end;
            else
                v_u_7 = v_u_2:clamp(v_u_7 + p39, 0, v40)
            end;
            v_u_26(v_u_7)
            p38:page_update()
        end;
        v5.get_current_page = function(_) --[[ Name: get_current_page ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_6 ]]
            return math.floor(v_u_7 / v_u_6:count()) + 1;
        end;
        v5.get_max_page = function(_, p43) --[[ Name: get_max_page ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_6 ]]
            if p43 == nil then
                p43 = v_u_11():count()
            end;
            return math.max(1, (math.ceil(p43 / v_u_6:count())));
        end;
        v5.go_to_page = function(p44, p45) --[[ Name: go_to_page ]] --[[ Line: 92 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_3 ]]
            if p45 >= 1 then
                p44:apply_page_offset(v_u_6:count() * (p45 - 1))
            else
                v_u_3:warnf("ListAdapter:go_to_page(%d) invalid", p45)
            end;
        end;
        v5.get_page_of_element = function(_, p46) --[[ Name: get_page_of_element ]] --[[ Line: 100 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_6 ]]
            local v47 = v_u_11():find(p46)
            return v47 == -1 and 1 or math.floor((v47 - 1) / v_u_6:count()) + 1;
        end;
        v5.update_next_prev_visible = function(_, p48) --[[ Name: update_next_prev_visible ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_31, (ref 3): v_u_17, (ref 4): v_u_7, (copy 5): v_u_6 ]]
            if p48 == nil then
                p48 = v_u_11():count()
            end;
            if v_u_31 then
                v_u_17(true, true)
            else
                v_u_17(p48 - v_u_7 > v_u_6:count(), v_u_7 > 0)
            end;
        end;
        v5.page_update = function(p49) --[[ Name: page_update ]] --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_7, (copy 3): v_u_6, (ref 4): v_u_14, (ref 5): v_u_23, (ref 6): v_u_20 ]]
            local v50 = v_u_11()
            local v51 = v50:count()
            if v51 <= v_u_7 then
                local v52
                if v_u_6:count() == 0 then
                    v52 = 0
                else
                    local v53 = (math.ceil(v51 / v_u_6:count()) - 1) * v_u_6:count()
                    v52 = v53 < 0 and 0 or v53
                end;
                v_u_7 = v52
            end;
            for v54 = 1, v_u_6:count() do
                local v55 = v_u_6:get(v54)
                local v56 = v54 + v_u_7
                if v56 <= v50:count() then
                    v_u_14(v55, v50:get(v56), v56, v54)
                else
                    v_u_14(v55, nil, v56, v54)
                end;
            end;
            v_u_23(v50:count() == 0)
            p49:update_next_prev_visible()
            v_u_20(p49:get_current_page(), p49:get_max_page(v51))
        end;
        v5.push_display_element = function(_, p57) --[[ Name: push_display_element ]] --[[ Line: 148 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            v_u_6:push_back(p57)
        end;
        v5.layout = function(_) --[[ Name: layout ]] --[[ Line: 152 ]]
            --[[ Upvalues: (copy 1): v_u_6 ]]
            for v58 = 1, v_u_6:count() do
                v_u_6:get(v58):layout()
            end;
        end;
        v5.set_visible = function(_, p59) --[[ Name: set_visible ]] --[[ Line: 158 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_11, (ref 3): v_u_17, (ref 4): v_u_7 ]]
            for v60 = 1, v_u_6:count() do
                v_u_6:get(v60):set_visible(p59)
            end;
            if p59 then
                v_u_17(v_u_11():count() - v_u_7 > v_u_6:count(), v_u_7 > 0)
            else
                v_u_17(false, false)
            end;
        end;
        v5.create_list_elements_from_anchors_and_proto = function(p61, p62, p63, p64, p65) --[[ Name: create_list_elements_from_anchors_and_proto ]] --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_1 ]]
            p63.Parent = nil
            if p63.ClassName == "Model" and p63.PrimaryPart ~= nil then
                for _, v66 in v_u_2:get_list_of_children_of_classname(p63.PrimaryPart, "SurfaceGui"):key_itr() do
                    v66.Enabled = true
                end;
            end;
            for _, v67 in v_u_1:new():push_back_table_list(p62):key_itr() do
                v67.Parent = nil
                local v68 = p63:Clone()
                if v67.ClassName == "Model" then
                    v68:SetPrimaryPartCFrame(v67.PrimaryPart.CFrame)
                elseif v67:IsA("BasePart") then
                    v68:SetPrimaryPartCFrame(v67.CFrame)
                end;
                v68.Parent = p64
                p61:push_display_element((p65(v68)))
            end;
        end;
        v5.refresh_element_data = function(_, p69) --[[ Name: refresh_element_data ]] --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_6, (ref 3): v_u_7 ]]
            local v70 = v_u_11()
            for v71 = 1, v_u_6:count() do
                local v72 = v_u_6:get(v71)
                local v73 = v71 + v_u_7
                if v73 <= v70:count() then
                    p69(v72, v70:get(v73), v73, v71)
                else
                    p69(v72, nil, v73, v71)
                end;
            end;
        end;
        v5.dbg_str = function(_) --[[ Name: dbg_str ]] --[[ Line: 212 ]]
            --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_7, (ref 3): v_u_11 ]]
            return string.format("ListAdapter _display_elements(%d) _i_offset(%d) _fn_get_data_list(%d)", v_u_6:count(), v_u_7, v_u_11():count());
        end;
        return v5;
    end,
    ["ButtonElement"] = {},
    ["DisplayElement"] = {},
    ["SavePageState"] = {}
}
v74.ButtonElement.new = function(_, p_u_75, p_u_76) --[[ Name: new ]] --[[ Line: 220 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    local v_u_77 = {}
    local function _() --[[ Name: cons ]] --[[ Line: 223 ]]
        --[[ Upvalues: (copy 1): p_u_76, (copy 2): v_u_77 ]]
        if p_u_76 then
            p_u_76(v_u_77)
        end;
    end;
    v_u_77.get_button = function(_) --[[ Name: get_button ]] --[[ Line: 227 ]]
        --[[ Upvalues: (copy 1): p_u_75 ]]
        return p_u_75;
    end;
    local v_u_78 = nil
    v_u_77.set_fn_set_display_element = function(p79, p80) --[[ Name: set_fn_set_display_element ]] --[[ Line: 230 ]]
        --[[ Upvalues: (ref 1): v_u_78 ]]
        v_u_78 = p80
        return p79;
    end;
    v_u_77.set_display_element = function(_, p81) --[[ Name: set_display_element ]] --[[ Line: 231 ]]
        --[[ Upvalues: (ref 1): v_u_78 ]]
        if v_u_78 then
            v_u_78(p81)
        end;
    end;
    local v_u_82 = nil
    v_u_77.set_fn_set_visible = function(p83, p84) --[[ Name: set_fn_set_visible ]] --[[ Line: 236 ]]
        --[[ Upvalues: (ref 1): v_u_82 ]]
        v_u_82 = p84
        return p83;
    end;
    v_u_77.set_visible = function(_, p85) --[[ Name: set_visible ]] --[[ Line: 237 ]]
        --[[ Upvalues: (copy 1): p_u_75, (ref 2): v_u_82 ]]
        p_u_75:set_visible(p85)
        if v_u_82 then
            v_u_82(p85)
        end;
    end;
    local v_u_86 = nil
    v_u_77.set_fn_layout = function(p87, p88) --[[ Name: set_fn_layout ]] --[[ Line: 243 ]]
        --[[ Upvalues: (ref 1): v_u_86 ]]
        v_u_86 = p88
        return p87;
    end;
    v_u_77.layout = function(_) --[[ Name: layout ]] --[[ Line: 244 ]]
        --[[ Upvalues: (ref 1): v_u_86 ]]
        if v_u_86 then
            v_u_86()
        end;
    end;
    local function v_u_89() --[[ Line: 249 ]]
        return 1;
    end;
    v_u_77.set_fn_get_parent_alpha = function(p90, p91) --[[ Name: set_fn_get_parent_alpha ]] --[[ Line: 250 ]]
        --[[ Upvalues: (ref 1): v_u_89 ]]
        v_u_89 = p91
        return p90;
    end;
    local v_u_92 = 1
    v_u_77.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 256 ]]
        --[[ Upvalues: (ref 1): v_u_92 ]]
        return v_u_92;
    end;
    local v_u_93 = nil
    local v_u_94 = nil
    v_u_77.set_alpha = function(p95, p96) --[[ Name: set_alpha ]] --[[ Line: 259 ]]
        --[[ Upvalues: (ref 1): v_u_93, (ref 2): v_u_94, (ref 3): v_u_2, (copy 4): p_u_75, (ref 5): v_u_92, (ref 6): v_u_89 ]]
        if v_u_93 == nil or v_u_94 == nil then
            v_u_93 = v_u_2:get_list_of_children_of_classname(p_u_75:get_part(), "ImageLabel")
            v_u_94 = v_u_2:get_list_of_children_of_classname(p_u_75:get_part(), "TextLabel")
        end;
        if p96 ~= v_u_92 then
            v_u_92 = p96
            v_u_2:list_set_alpha_name(v_u_93, {
                ["ImageAlpha"] = v_u_92
            })
            v_u_2:list_set_alpha_name(v_u_94, {
                ["TextAlpha"] = v_u_92
            })
            v_u_2:r_set_alpha(p_u_75:get_part(), v_u_89())
        end;
        return p95;
    end;
    if p_u_76 then
        p_u_76(v_u_77)
    end;
    return v_u_77;
end;
v74.DisplayElement.new = function(_, p_u_97, p_u_98, p_u_99, p_u_100) --[[ Name: new ]] --[[ Line: 278 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2 ]]
    local v_u_101 = {}
    local v_u_102 = nil
    local function _() --[[ Name: cons ]] --[[ Line: 283 ]]
        --[[ Upvalues: (ref 1): v_u_102, (ref 2): v_u_4, (copy 3): p_u_97, (copy 4): p_u_98, (copy 5): p_u_99, (copy 6): p_u_100, (copy 7): v_u_101 ]]
        v_u_102 = v_u_4:new(p_u_97, p_u_98, p_u_99.PrimaryPart):set_default_sgui()
        if p_u_100 then
            p_u_100(v_u_101)
        end;
    end;
    v_u_101.get_uichild = function(_) --[[ Name: get_uichild ]] --[[ Line: 288 ]]
        --[[ Upvalues: (ref 1): v_u_102 ]]
        return v_u_102;
    end;
    v_u_101.get_obj = function(_) --[[ Name: get_obj ]] --[[ Line: 289 ]]
        --[[ Upvalues: (copy 1): p_u_99 ]]
        return p_u_99;
    end;
    local v_u_103 = nil
    v_u_101.set_fn_set_display_element = function(p104, p105) --[[ Name: set_fn_set_display_element ]] --[[ Line: 292 ]]
        --[[ Upvalues: (ref 1): v_u_103 ]]
        v_u_103 = p105
        return p104;
    end;
    v_u_101.set_display_element = function(_, p106) --[[ Name: set_display_element ]] --[[ Line: 293 ]]
        --[[ Upvalues: (ref 1): v_u_103 ]]
        if v_u_103 then
            v_u_103(p106)
        end;
    end;
    local v_u_107 = nil
    v_u_101.set_fn_set_visible = function(p108, p109) --[[ Name: set_fn_set_visible ]] --[[ Line: 298 ]]
        --[[ Upvalues: (ref 1): v_u_107 ]]
        v_u_107 = p109
        return p108;
    end;
    v_u_101.set_visible = function(_, p110) --[[ Name: set_visible ]] --[[ Line: 299 ]]
        --[[ Upvalues: (ref 1): v_u_102, (ref 2): v_u_107 ]]
        v_u_102:set_visible(p110)
        if v_u_107 then
            v_u_107(p110)
        end;
    end;
    local v_u_111 = nil
    v_u_101.set_fn_layout = function(p112, p113) --[[ Name: set_fn_layout ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): v_u_111 ]]
        v_u_111 = p113
        return p112;
    end;
    v_u_101.layout = function(_) --[[ Name: layout ]] --[[ Line: 306 ]]
        --[[ Upvalues: (ref 1): v_u_102, (ref 2): v_u_111 ]]
        v_u_102:layout()
        if v_u_111 then
            v_u_111()
        end;
    end;
    local function v_u_114() --[[ Line: 311 ]]
        return 1;
    end;
    v_u_101.set_fn_get_parent_alpha = function(p115, p116) --[[ Name: set_fn_get_parent_alpha ]] --[[ Line: 312 ]]
        --[[ Upvalues: (ref 1): v_u_114 ]]
        v_u_114 = p116
        return p115;
    end;
    local v_u_117 = 1
    v_u_101.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 318 ]]
        --[[ Upvalues: (ref 1): v_u_117 ]]
        return v_u_117;
    end;
    local v_u_118 = nil
    local v_u_119 = nil
    v_u_101.set_alpha = function(p120, p121) --[[ Name: set_alpha ]] --[[ Line: 321 ]]
        --[[ Upvalues: (ref 1): v_u_118, (ref 2): v_u_119, (ref 3): v_u_2, (copy 4): p_u_99, (ref 5): v_u_117, (ref 6): v_u_114 ]]
        if v_u_118 == nil or v_u_119 == nil then
            v_u_118 = v_u_2:get_list_of_children_of_classname(p_u_99, "ImageLabel")
            v_u_119 = v_u_2:get_list_of_children_of_classname(p_u_99, "TextLabel")
        end;
        if p121 ~= v_u_117 then
            v_u_117 = p121
            v_u_2:list_set_alpha_name(v_u_118, {
                ["ImageAlpha"] = v_u_117
            })
            v_u_2:list_set_alpha_name(v_u_119, {
                ["TextAlpha"] = v_u_117
            })
            v_u_2:r_set_alpha(p_u_99, v_u_114())
        end;
        return p120;
    end;
    v_u_102 = v_u_4:new(p_u_97, p_u_98, p_u_99.PrimaryPart):set_default_sgui()
    if p_u_100 then
        p_u_100(v_u_101)
    end;
    return v_u_101;
end;
v74.SavePageState.new = function(_) --[[ Name: new ]] --[[ Line: 340 ]]
    local v122 = {}
    local v_u_123 = 1
    local v_u_124 = ""
    v122.open_to_saved_page = function(_, p125, p126) --[[ Name: open_to_saved_page ]] --[[ Line: 345 ]]
        --[[ Upvalues: (ref 1): v_u_124, (ref 2): v_u_123 ]]
        local v127 = p126 == nil and "" or p126
        if v127 == v_u_124 then
            p125:go_to_page(v_u_123)
        end;
        v_u_124 = v127
    end;
    v122.on_list_select_save_page = function(_, p128, p129) --[[ Name: on_list_select_save_page ]] --[[ Line: 353 ]]
        --[[ Upvalues: (ref 1): v_u_123, (ref 2): v_u_124 ]]
        v_u_123 = p128:get_current_page()
        if p129 ~= nil then
            v_u_124 = p129
        end;
    end;
    return v122;
end;
return v74;
