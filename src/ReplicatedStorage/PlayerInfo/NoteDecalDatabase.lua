-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:12 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = {
    ["NoteDecalInfoBase"] = {}
}
v_u_4.NoteDecalInfoBase.new = function(_) --[[ Name: new ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
    local v5 = {
        ["get_name"] = function(_) --[[ Name: get_name ]] --[[ Line: 15 ]]
            return "Default";
        end,
        ["get_trigger_back_assetid"] = function(_, _) --[[ Name: get_trigger_back_assetid ]] --[[ Line: 18 ]]
            return "rbxassetid://8066626716";
        end,
        ["get_trigger_mid_assetid"] = function(_, _) --[[ Name: get_trigger_mid_assetid ]] --[[ Line: 19 ]]
            return "rbxassetid://8066629002";
        end,
        ["get_trigger_over_assetid"] = function(_, _) --[[ Name: get_trigger_over_assetid ]] --[[ Line: 20 ]]
            return "rbxassetid://8057932157";
        end,
        ["get_single_note_fill_assetid"] = function(_, _) --[[ Name: get_single_note_fill_assetid ]] --[[ Line: 22 ]]
            return "rbxassetid://8083819466";
        end,
        ["get_single_note_outline_assetid"] = function(_, _) --[[ Name: get_single_note_outline_assetid ]] --[[ Line: 23 ]]
            return "rbxassetid://8083829743";
        end,
        ["get_held_note_fill_assetid"] = function(_, _) --[[ Name: get_held_note_fill_assetid ]] --[[ Line: 25 ]]
            return "rbxassetid://8066691104";
        end,
        ["get_held_note_outline_assetid"] = function(_, _) --[[ Name: get_held_note_outline_assetid ]] --[[ Line: 26 ]]
            return "rbxassetid://8066690947";
        end,
        ["get_held_note_body_assetid"] = function(_, _) --[[ Name: get_held_note_body_assetid ]] --[[ Line: 27 ]]
            return "rbxassetid://8066791263";
        end,
        ["get_hit_effect_assetid"] = function(_) --[[ Name: get_hit_effect_assetid ]] --[[ Line: 29 ]]
            return "rbxassetid://8089802049";
        end,
        ["get_note_size_scale"] = function(_) --[[ Name: get_note_size_scale ]] --[[ Line: 31 ]]
            return 0.85;
        end,
        ["get_held_note_body_size_scale"] = function(_) --[[ Name: get_held_note_body_size_scale ]] --[[ Line: 32 ]]
            return 0.4;
        end,
        ["apply_color_to_trigger_mid"] = function(_) --[[ Name: apply_color_to_trigger_mid ]] --[[ Line: 33 ]]
            return true;
        end
    }
    local v_u_6 = -1
    v5.set_id = function(_, p7) --[[ Name: set_id ]] --[[ Line: 13 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        v_u_6 = p7
    end;
    v5.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 14 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        return v_u_6;
    end;
    v5.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 16 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        return v_u_2:important_assetid();
    end;
    v5.get_assetid_table = function(p8) --[[ Name: get_assetid_table ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v9 = v_u_1:new()
        for v10 = 1, 4 do
            v9:add_set(p8:get_single_note_fill_assetid(v10))
            v9:add_set(p8:get_single_note_outline_assetid(v10))
            v9:add_set(p8:get_held_note_fill_assetid(v10))
            v9:add_set(p8:get_held_note_outline_assetid(v10))
            v9:add_set(p8:get_held_note_body_assetid(v10))
            v9:add_set(p8:get_trigger_back_assetid(v10))
            v9:add_set(p8:get_trigger_mid_assetid(v10))
            v9:add_set(p8:get_trigger_over_assetid(v10))
            v9:add_set(p8:get_hit_effect_assetid(v10))
        end;
        return v9:key_list()._table;
    end;
    return v5;
end;
v_u_4.new = function(_) --[[ Name: new ]] --[[ Line: 54 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_3 ]]
    local v11 = {
        ["get_default_notedecal_id"] = function(_) --[[ Name: get_default_notedecal_id ]] --[[ Line: 225 ]]
            return 0;
        end
    }
    local v_u_12 = v_u_1:new()
    v11.cons = function(p13) --[[ Name: cons ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
        local v14 = v_u_4.NoteDecalInfoBase:new()
        v14.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 62 ]]
            return "rbxassetid://8928962763";
        end;
        p13:add_notedecal_for_id(0, v14)
        p13:add_notedecal_for_id(1, ((function() --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v15 = v_u_4.NoteDecalInfoBase:new()
            v15.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 68 ]]
                return "Circles";
            end;
            v15.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 69 ]]
                return "rbxassetid://8928963351";
            end;
            v15.get_trigger_back_assetid = function(_, _) --[[ Name: get_trigger_back_assetid ]] --[[ Line: 71 ]]
                return "rbxassetid://8233162165";
            end;
            v15.get_trigger_mid_assetid = function(_, _) --[[ Name: get_trigger_mid_assetid ]] --[[ Line: 72 ]]
                return "rbxassetid://8233162252";
            end;
            v15.get_trigger_over_assetid = function(_, _) --[[ Name: get_trigger_over_assetid ]] --[[ Line: 73 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v15.get_single_note_fill_assetid = function(_, _) --[[ Name: get_single_note_fill_assetid ]] --[[ Line: 75 ]]
                return "rbxassetid://8233162252";
            end;
            v15.get_single_note_outline_assetid = function(_, _) --[[ Name: get_single_note_outline_assetid ]] --[[ Line: 76 ]]
                return "rbxassetid://8233162165";
            end;
            v15.get_held_note_fill_assetid = function(p16, p17) --[[ Name: get_held_note_fill_assetid ]] --[[ Line: 78 ]]
                return p16:get_single_note_fill_assetid(p17);
            end;
            v15.get_held_note_outline_assetid = function(p18, p19) --[[ Name: get_held_note_outline_assetid ]] --[[ Line: 79 ]]
                return p18:get_single_note_outline_assetid(p19);
            end;
            v15.get_held_note_body_assetid = function(_, _) --[[ Name: get_held_note_body_assetid ]] --[[ Line: 80 ]]
                return "rbxassetid://8066791263";
            end;
            return v15;
        end)()))
        p13:add_notedecal_for_id(2, ((function() --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v20 = v_u_4.NoteDecalInfoBase:new()
            v20.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 85 ]]
                return "Bars";
            end;
            v20.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 86 ]]
                return "rbxassetid://8929064834";
            end;
            v20.get_trigger_back_assetid = function(_, _) --[[ Name: get_trigger_back_assetid ]] --[[ Line: 88 ]]
                return "rbxassetid://8240223027";
            end;
            v20.get_trigger_mid_assetid = function(_, _) --[[ Name: get_trigger_mid_assetid ]] --[[ Line: 89 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v20.get_trigger_over_assetid = function(_, _) --[[ Name: get_trigger_over_assetid ]] --[[ Line: 90 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v20.get_single_note_fill_assetid = function(_, _) --[[ Name: get_single_note_fill_assetid ]] --[[ Line: 92 ]]
                return "rbxassetid://8240223174";
            end;
            v20.get_single_note_outline_assetid = function(_, _) --[[ Name: get_single_note_outline_assetid ]] --[[ Line: 93 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v20.get_held_note_fill_assetid = function(p21, p22) --[[ Name: get_held_note_fill_assetid ]] --[[ Line: 95 ]]
                return p21:get_single_note_fill_assetid(p22);
            end;
            v20.get_held_note_outline_assetid = function(p23, p24) --[[ Name: get_held_note_outline_assetid ]] --[[ Line: 96 ]]
                return p23:get_single_note_outline_assetid(p24);
            end;
            v20.get_held_note_body_assetid = function(_, _) --[[ Name: get_held_note_body_assetid ]] --[[ Line: 97 ]]
                return "rbxassetid://8240223305";
            end;
            v20.get_note_size_scale = function(_) --[[ Name: get_note_size_scale ]] --[[ Line: 98 ]]
                return 1;
            end;
            v20.get_held_note_body_size_scale = function(_) --[[ Name: get_held_note_body_size_scale ]] --[[ Line: 99 ]]
                return 0.75;
            end;
            return v20;
        end)()))
        p13:add_notedecal_for_id(3, ((function() --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v25 = v_u_4.NoteDecalInfoBase:new()
            v25.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 104 ]]
                return "Arrows";
            end;
            v25.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 105 ]]
                return "rbxassetid://8928962137";
            end;
            v25.get_trigger_back_assetid = function(_, _) --[[ Name: get_trigger_back_assetid ]] --[[ Line: 107 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v25.get_trigger_mid_assetid = function(_, p26) --[[ Name: get_trigger_mid_assetid ]] --[[ Line: 108 ]]
                return p26 == 1 and "rbxassetid://8241232736" or (p26 == 2 and "rbxassetid://8241232652" or (p26 == 3 and "rbxassetid://8241232493" or "rbxassetid://8241232268"));
            end;
            v25.get_trigger_over_assetid = function(_, _) --[[ Name: get_trigger_over_assetid ]] --[[ Line: 119 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v25.apply_color_to_trigger_mid = function(_) --[[ Name: apply_color_to_trigger_mid ]] --[[ Line: 120 ]]
                return false;
            end;
            v25.get_single_note_fill_assetid = function(_, p27) --[[ Name: get_single_note_fill_assetid ]] --[[ Line: 122 ]]
                return p27 == 1 and "rbxassetid://8241234214" or (p27 == 2 and "rbxassetid://8241234052" or (p27 == 3 and "rbxassetid://8241233788" or "rbxassetid://8241233515"));
            end;
            v25.get_single_note_outline_assetid = function(_, p28) --[[ Name: get_single_note_outline_assetid ]] --[[ Line: 133 ]]
                return p28 == 1 and "rbxassetid://8241233367" or (p28 == 2 and "rbxassetid://8241233255" or (p28 == 3 and "rbxassetid://8241233100" or "rbxassetid://8241232912"));
            end;
            v25.get_held_note_fill_assetid = function(p29, p30) --[[ Name: get_held_note_fill_assetid ]] --[[ Line: 145 ]]
                return p29:get_single_note_fill_assetid(p30);
            end;
            v25.get_held_note_outline_assetid = function(p31, p32) --[[ Name: get_held_note_outline_assetid ]] --[[ Line: 146 ]]
                return p31:get_single_note_outline_assetid(p32);
            end;
            v25.get_held_note_body_assetid = function(_, _) --[[ Name: get_held_note_body_assetid ]] --[[ Line: 147 ]]
                return "rbxassetid://8066791263";
            end;
            return v25;
        end)()))
        p13:add_notedecal_for_id(4, ((function() --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v33 = v_u_4.NoteDecalInfoBase:new()
            v33.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 152 ]]
                return "Arrows (FNF)";
            end;
            v33.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 153 ]]
                return "rbxassetid://8928962552";
            end;
            v33.get_trigger_back_assetid = function(_, _) --[[ Name: get_trigger_back_assetid ]] --[[ Line: 155 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v33.get_trigger_mid_assetid = function(_, p34) --[[ Name: get_trigger_mid_assetid ]] --[[ Line: 156 ]]
                return p34 == 1 and "rbxassetid://8233340493" or (p34 == 2 and "rbxassetid://8233340337" or (p34 == 3 and "rbxassetid://8233340202" or "rbxassetid://8233340077"));
            end;
            v33.get_trigger_over_assetid = function(_, _) --[[ Name: get_trigger_over_assetid ]] --[[ Line: 167 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v33.apply_color_to_trigger_mid = function(_) --[[ Name: apply_color_to_trigger_mid ]] --[[ Line: 168 ]]
                return false;
            end;
            v33.get_single_note_fill_assetid = function(_, p35) --[[ Name: get_single_note_fill_assetid ]] --[[ Line: 170 ]]
                return p35 == 1 and "rbxassetid://8233341421" or (p35 == 2 and "rbxassetid://8233341323" or (p35 == 3 and "rbxassetid://8233341238" or "rbxassetid://8233341134"));
            end;
            v33.get_single_note_outline_assetid = function(_, p36) --[[ Name: get_single_note_outline_assetid ]] --[[ Line: 181 ]]
                return p36 == 1 and "rbxassetid://8233341013" or (p36 == 2 and "rbxassetid://8233340878" or (p36 == 3 and "rbxassetid://8233340771" or "rbxassetid://8233340666"));
            end;
            v33.get_held_note_fill_assetid = function(p37, p38) --[[ Name: get_held_note_fill_assetid ]] --[[ Line: 193 ]]
                return p37:get_single_note_fill_assetid(p38);
            end;
            v33.get_held_note_outline_assetid = function(p39, p40) --[[ Name: get_held_note_outline_assetid ]] --[[ Line: 194 ]]
                return p39:get_single_note_outline_assetid(p40);
            end;
            v33.get_held_note_body_assetid = function(_, _) --[[ Name: get_held_note_body_assetid ]] --[[ Line: 195 ]]
                return "rbxassetid://8066791263";
            end;
            v33.get_note_size_scale = function(_) --[[ Name: get_note_size_scale ]] --[[ Line: 196 ]]
                return 1;
            end;
            return v33;
        end)()))
        p13:add_notedecal_for_id(5, ((function() --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_2 ]]
            local v41 = v_u_4.NoteDecalInfoBase:new()
            v41.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 201 ]]
                return "Diamonds";
            end;
            v41.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 202 ]]
                return "rbxassetid://8928962398";
            end;
            v41.get_trigger_back_assetid = function(_, _) --[[ Name: get_trigger_back_assetid ]] --[[ Line: 204 ]]
                return "rbxassetid://8240330575";
            end;
            v41.get_trigger_mid_assetid = function(_, _) --[[ Name: get_trigger_mid_assetid ]] --[[ Line: 205 ]]
                return "rbxassetid://8240330395";
            end;
            v41.get_trigger_over_assetid = function(_, _) --[[ Name: get_trigger_over_assetid ]] --[[ Line: 206 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                return v_u_2:transparent_assetid();
            end;
            v41.get_single_note_fill_assetid = function(_, _) --[[ Name: get_single_note_fill_assetid ]] --[[ Line: 208 ]]
                return "rbxassetid://8240330395";
            end;
            v41.get_single_note_outline_assetid = function(_, _) --[[ Name: get_single_note_outline_assetid ]] --[[ Line: 209 ]]
                return "rbxassetid://8240371737";
            end;
            v41.get_held_note_fill_assetid = function(p42, p43) --[[ Name: get_held_note_fill_assetid ]] --[[ Line: 211 ]]
                return p42:get_single_note_fill_assetid(p43);
            end;
            v41.get_held_note_outline_assetid = function(p44, p45) --[[ Name: get_held_note_outline_assetid ]] --[[ Line: 212 ]]
                return p44:get_single_note_outline_assetid(p45);
            end;
            v41.get_held_note_body_assetid = function(_, _) --[[ Name: get_held_note_body_assetid ]] --[[ Line: 213 ]]
                return "rbxassetid://8066791263";
            end;
            v41.get_note_size_scale = function(_) --[[ Name: get_note_size_scale ]] --[[ Line: 214 ]]
                return 1;
            end;
            return v41;
        end)()))
    end;
    v11.add_notedecal_for_id = function(_, p46, p47) --[[ Name: add_notedecal_for_id ]] --[[ Line: 219 ]]
        --[[ Upvalues: (copy 1): v_u_12, (ref 2): v_u_3 ]]
        if v_u_12:contains(p46) then
            v_u_3:errf("_id_to_decal_info already contains(%d)", p46)
        end;
        p47:set_id(p46)
        v_u_12:add(p46, p47)
    end;
    v11.get_default_notedecal_info = function(p48) --[[ Name: get_default_notedecal_info ]] --[[ Line: 229 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:get(p48:get_default_notedecal_id());
    end;
    v11.contains_id = function(_, p49) --[[ Name: contains_id ]] --[[ Line: 233 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:contains(p49);
    end;
    v11.get_info_for_id = function(_, p50) --[[ Name: get_info_for_id ]] --[[ Line: 237 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return v_u_12:get(p50);
    end;
    v11.get_preload_assetid_table = function(_) --[[ Name: get_preload_assetid_table ]] --[[ Line: 241 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_12 ]]
        local v51 = v_u_1:new()
        for _, v52 in v_u_12:key_itr() do
            for _, v53 in pairs(v52:get_assetid_table()) do
                v51:add_set(v53)
            end;
        end;
        return v51:key_list()._table;
    end;
    v11:cons()
    return v11;
end;
local v_u_54 = v_u_4:new()
v_u_4.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 256 ]]
    --[[ Upvalues: (copy 1): v_u_54 ]]
    return v_u_54;
end;
return v_u_4;
