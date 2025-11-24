-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:06 PM
-- Time elapsed: 82 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = {
    ["FeverIconDisplay"] = {
        ["Stars"] = 1,
        ["None"] = 2,
        ["Icon"] = 3
    },
    ["FeverIconInfoBase"] = {}
}
local v_u_6 = v_u_3:invalid_material_id()
v_u_5.FeverIconInfoBase.new = function(_) --[[ Name: new ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_6 ]]
    local v7 = {
        ["is_vip_only"] = function(_) --[[ Name: is_vip_only ]] --[[ Line: 26 ]]
            return false;
        end
    }
    local v_u_8 = -1
    v7.set_id = function(_, p9) --[[ Name: set_id ]] --[[ Line: 20 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        v_u_8 = p9
    end;
    v7.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 21 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        return v_u_8;
    end;
    v7.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 22 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        v_u_4:errf("FeverIconDatabase.FeverIconInfoBase must implement get_name")
    end;
    v7.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 23 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        v_u_4:errf("FeverIconDatabase.FeverIconInfoBase must implement get_icon")
    end;
    v7.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 24 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        v_u_4:errf("FeverIconDatabase.FeverIconInfoBase must implement get_image")
    end;
    v7.apply_to_emitter = function(_) --[[ Name: apply_to_emitter ]] --[[ Line: 25 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        v_u_4:errf("FeverIconDatabase.FeverIconInfoBase must implement apply_to_emitter")
    end;
    local v_u_10 = v_u_6
    v7.set_material_id = function(_, p11) --[[ Name: set_material_id ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        v_u_10 = p11
    end;
    v7.get_material_id = function(_) --[[ Name: get_material_id ]] --[[ Line: 30 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        return v_u_10;
    end;
    return v7;
end;
local function f_apply_default_emitter_properties(p12) --[[ Name: apply_default_emitter_properties ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    p12.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)), ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 0, 0)) })
    p12.Size = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 0),
        NumberSequenceKeypoint.new(0.0302, 0.188),
        NumberSequenceKeypoint.new(0.0506, 0.375),
        NumberSequenceKeypoint.new(0.0816, 0.125),
        NumberSequenceKeypoint.new(0.108, 0.125),
        NumberSequenceKeypoint.new(0.129, 0.25),
        NumberSequenceKeypoint.new(0.418, 0),
        NumberSequenceKeypoint.new(1, 0)
    })
    p12.Texture = v_u_3:get_sparkle_star_white_assetid()
    p12.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.562), NumberSequenceKeypoint.new(1, 1) })
    p12.Lifetime = NumberRange.new(1, 1.1)
    p12.Rate = 40
    p12.Rotation = NumberRange.new(-45, 45)
    p12.RotSpeed = NumberRange.new(-5, 5)
    p12.Speed = NumberRange.new(1, 2)
    p12.SpreadAngle = Vector2.new(0, 0)
    p12.Enabled = true
end;
local function f_apply_simple_size_anim(p13) --[[ Name: apply_simple_size_anim ]] --[[ Line: 64 ]]
    p13.Size = NumberSequence.new({
        NumberSequenceKeypoint.new(0, 0),
        NumberSequenceKeypoint.new(0.4, 0.165),
        NumberSequenceKeypoint.new(0.55, 0.12),
        NumberSequenceKeypoint.new(0.7, 0),
        NumberSequenceKeypoint.new(1, 0)
    })
end;
local function f_apply_simple_transparency_anim(p14) --[[ Name: apply_simple_transparency_anim ]] --[[ Line: 74 ]]
    p14.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.65), NumberSequenceKeypoint.new(1, 1) })
end;
local function _(p15) --[[ Name: apply_no_initial_rotation ]] --[[ Line: 81 ]]
    p15.Rotation = NumberRange.new(0, 0)
end;
v_u_5.new = function(_) --[[ Name: new ]] --[[ Line: 85 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_5, (copy 4): f_apply_default_emitter_properties, (copy 5): f_apply_simple_size_anim, (copy 6): f_apply_simple_transparency_anim, (copy 7): v_u_3, (copy 8): v_u_4 ]]
    local v_u_17 = {
        ["get_stars_icon_id"] = function(_) --[[ Name: get_stars_icon_id ]] --[[ Line: 91 ]]
            return 0;
        end,
        ["get_disabled_icon_id"] = function(_) --[[ Name: get_disabled_icon_id ]] --[[ Line: 92 ]]
            return 1;
        end,
        ["get_default_fevericon"] = function(p16) --[[ Name: get_default_fevericon ]] --[[ Line: 2171 ]]
            return p16:get_fevericon_for_id(0);
        end
    }
    local v_u_18 = v_u_2:new()
    local v_u_19 = v_u_1:new()
    local v_u_20 = v_u_2:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 94 ]]
        --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_5, (ref 3): f_apply_default_emitter_properties, (ref 4): f_apply_simple_size_anim, (ref 5): f_apply_simple_transparency_anim, (ref 6): v_u_3, (copy 7): v_u_19, (copy 8): v_u_20 ]]
        local function _(p21, p_u_22, p_u_23, p_u_24) --[[ Name: add_icon ]] --[[ Line: 95 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_5, (ref 3): f_apply_default_emitter_properties, (ref 4): f_apply_simple_size_anim, (ref 5): f_apply_simple_transparency_anim ]]
            v_u_17:add_fevericon_for_id(p21, ((function() --[[ Line: 96 ]]
                --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_22, (copy 3): p_u_23, (copy 4): p_u_24, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
                local v25 = v_u_5.FeverIconInfoBase:new()
                v25.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                    --[[ Upvalues: (ref 1): p_u_22 ]]
                    return p_u_22;
                end;
                v25.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                    --[[ Upvalues: (ref 1): p_u_23 ]]
                    return p_u_23;
                end;
                v25.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                    --[[ Upvalues: (ref 1): p_u_24 ]]
                    return p_u_24;
                end;
                v25.apply_to_emitter = function(p26, p27) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                    --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                    f_apply_default_emitter_properties(p27)
                    f_apply_simple_size_anim(p27)
                    f_apply_simple_transparency_anim(p27)
                    p27.Rate = 20
                    p27.Texture = p26:get_image()
                end;
                return v25;
            end)()))
        end;
        v_u_17:add_fevericon_for_id(v_u_17:get_stars_icon_id(), ((function() --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_3, (ref 3): f_apply_default_emitter_properties ]]
            local v28 = v_u_5.FeverIconInfoBase:new()
            v28.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 114 ]]
                return "Star Sparkles (Default)";
            end;
            v28.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 115 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3:get_sparkle_star_white_assetid();
            end;
            v28.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 116 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3:get_sparkle_star_white_assetid();
            end;
            v28.apply_to_emitter = function(_, p29) --[[ Name: apply_to_emitter ]] --[[ Line: 117 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties ]]
                f_apply_default_emitter_properties(p29)
            end;
            return v28;
        end)()))
        v_u_17:add_fevericon_for_id(v_u_17:get_disabled_icon_id(), ((function() --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_3 ]]
            local v30 = v_u_5.FeverIconInfoBase:new()
            v30.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 122 ]]
                return "Disabled";
            end;
            v30.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 123 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3:transparent_assetid();
            end;
            v30.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 124 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                return v_u_3:transparent_assetid();
            end;
            v30.apply_to_emitter = function(_, p31) --[[ Name: apply_to_emitter ]] --[[ Line: 125 ]]
                p31.Rate = 0
                p31.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 1), NumberSequenceKeypoint.new(1, 1) })
            end;
            return v30;
        end)()))
        v_u_17:add_fevericon_for_id(2, ((function() --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v32 = v_u_5.FeverIconInfoBase:new()
            v32.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 136 ]]
                return "Crown";
            end;
            v32.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 137 ]]
                return "rbxassetid://2849951893";
            end;
            v32.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 138 ]]
                return "rbxassetid://1812502124";
            end;
            v32.apply_to_emitter = function(_, p33) --[[ Name: apply_to_emitter ]] --[[ Line: 139 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p33)
                f_apply_simple_size_anim(p33)
                f_apply_simple_transparency_anim(p33)
                p33.Rate = 20
                p33.Texture = "rbxassetid://1812502124"
            end;
            return v32;
        end)()))
        v_u_17:add_fevericon_for_id(3, ((function() --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v34 = v_u_5.FeverIconInfoBase:new()
            v34.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 150 ]]
                return "Trophy";
            end;
            v34.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 151 ]]
                return "rbxassetid://2849951455";
            end;
            v34.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 152 ]]
                return "rbxassetid://1812502120";
            end;
            v34.apply_to_emitter = function(_, p35) --[[ Name: apply_to_emitter ]] --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p35)
                f_apply_simple_size_anim(p35)
                f_apply_simple_transparency_anim(p35)
                p35.Rate = 20
                p35.Texture = "rbxassetid://1812502120"
            end;
            return v34;
        end)()))
        v_u_17:add_fevericon_for_id(4, ((function() --[[ Line: 162 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v36 = v_u_5.FeverIconInfoBase:new()
            v36.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 164 ]]
                return "Trash";
            end;
            v36.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 165 ]]
                return "rbxassetid://2849951192";
            end;
            v36.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 166 ]]
                return "rbxassetid://2813390949";
            end;
            v36.apply_to_emitter = function(_, p37) --[[ Name: apply_to_emitter ]] --[[ Line: 167 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p37)
                f_apply_simple_size_anim(p37)
                f_apply_simple_transparency_anim(p37)
                p37.Rate = 20
                p37.Texture = "rbxassetid://2813390949"
            end;
            return v36;
        end)()))
        v_u_17:add_fevericon_for_id(5, ((function() --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v38 = v_u_5.FeverIconInfoBase:new()
            v38.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 178 ]]
                return "Coin";
            end;
            v38.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 179 ]]
                return "rbxassetid://2849950977";
            end;
            v38.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 180 ]]
                return "rbxassetid://818988511";
            end;
            v38.apply_to_emitter = function(_, p39) --[[ Name: apply_to_emitter ]] --[[ Line: 181 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p39)
                f_apply_simple_size_anim(p39)
                f_apply_simple_transparency_anim(p39)
                p39.Rate = 20
                p39.Texture = "rbxassetid://818988511"
            end;
            return v38;
        end)()))
        v_u_17:add_fevericon_for_id(6, ((function() --[[ Line: 190 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v40 = v_u_5.FeverIconInfoBase:new()
            v40.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 192 ]]
                return "Eye";
            end;
            v40.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 193 ]]
                return "rbxassetid://2849950775";
            end;
            v40.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 194 ]]
                return "rbxassetid://1622425692";
            end;
            v40.apply_to_emitter = function(_, p41) --[[ Name: apply_to_emitter ]] --[[ Line: 195 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p41)
                f_apply_simple_size_anim(p41)
                f_apply_simple_transparency_anim(p41)
                p41.Rate = 20
                p41.Texture = "rbxassetid://1622425692"
            end;
            return v40;
        end)()))
        v_u_17:add_fevericon_for_id(7, ((function() --[[ Line: 204 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v42 = v_u_5.FeverIconInfoBase:new()
            v42.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 206 ]]
                return "X";
            end;
            v42.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 207 ]]
                return "rbxassetid://2849950591";
            end;
            v42.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 208 ]]
                return "rbxassetid://1622427376";
            end;
            v42.apply_to_emitter = function(_, p43) --[[ Name: apply_to_emitter ]] --[[ Line: 209 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p43)
                f_apply_simple_size_anim(p43)
                f_apply_simple_transparency_anim(p43)
                p43.Rotation = NumberRange.new(0, 0)
                p43.Rate = 20
                p43.Texture = "rbxassetid://1622427376"
            end;
            return v42;
        end)()))
        v_u_17:add_fevericon_for_id(8, ((function() --[[ Line: 219 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v44 = v_u_5.FeverIconInfoBase:new()
            v44.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 221 ]]
                return "Money";
            end;
            v44.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 222 ]]
                return "rbxassetid://2849950411";
            end;
            v44.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 223 ]]
                return "rbxassetid://816676821";
            end;
            v44.apply_to_emitter = function(_, p45) --[[ Name: apply_to_emitter ]] --[[ Line: 224 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p45)
                f_apply_simple_size_anim(p45)
                f_apply_simple_transparency_anim(p45)
                p45.Rate = 20
                p45.Texture = "rbxassetid://816676821"
            end;
            return v44;
        end)()))
        v_u_17:add_fevericon_for_id(9, ((function() --[[ Line: 233 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v46 = v_u_5.FeverIconInfoBase:new()
            v46.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 235 ]]
                return "Star";
            end;
            v46.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 236 ]]
                return "rbxassetid://2849950234";
            end;
            v46.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 237 ]]
                return "rbxassetid://818988515";
            end;
            v46.apply_to_emitter = function(_, p47) --[[ Name: apply_to_emitter ]] --[[ Line: 238 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p47)
                f_apply_simple_size_anim(p47)
                f_apply_simple_transparency_anim(p47)
                p47.Rate = 20
                p47.Texture = "rbxassetid://818988515"
            end;
            return v46;
        end)()))
        v_u_17:add_fevericon_for_id(10, ((function() --[[ Line: 247 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v48 = v_u_5.FeverIconInfoBase:new()
            v48.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 249 ]]
                return "VIP";
            end;
            v48.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 250 ]]
                return "rbxassetid://2921415550";
            end;
            v48.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 251 ]]
                return "http://www.roblox.com/asset/?id=6423399512";
            end;
            v48.apply_to_emitter = function(_, p49) --[[ Name: apply_to_emitter ]] --[[ Line: 252 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p49)
                f_apply_simple_size_anim(p49)
                f_apply_simple_transparency_anim(p49)
                p49.Rate = 20
                p49.Texture = "rbxassetid://2921415550"
            end;
            v48.is_vip_only = function(_) --[[ Name: is_vip_only ]] --[[ Line: 259 ]]
                return true;
            end;
            return v48;
        end)()))
        v_u_17:add_fevericon_for_id(11, ((function() --[[ Line: 264 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v50 = v_u_5.FeverIconInfoBase:new()
            v50.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 266 ]]
                return "PogChamp";
            end;
            v50.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 267 ]]
                return "http://www.roblox.com/asset/?id=4791589654";
            end;
            v50.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 268 ]]
                return "http://www.roblox.com/asset/?id=4780022696";
            end;
            v50.apply_to_emitter = function(_, p51) --[[ Name: apply_to_emitter ]] --[[ Line: 269 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p51)
                f_apply_simple_size_anim(p51)
                f_apply_simple_transparency_anim(p51)
                p51.Rate = 20
                p51.Texture = "http://www.roblox.com/asset/?id=4780022696"
            end;
            return v50;
        end)()))
        v_u_17:add_fevericon_for_id(12, ((function() --[[ Line: 278 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v52 = v_u_5.FeverIconInfoBase:new()
            v52.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 280 ]]
                return "LUL";
            end;
            v52.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 281 ]]
                return "http://www.roblox.com/asset/?id=4791573978";
            end;
            v52.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 282 ]]
                return "http://www.roblox.com/asset/?id=4780023117";
            end;
            v52.apply_to_emitter = function(_, p53) --[[ Name: apply_to_emitter ]] --[[ Line: 283 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p53)
                f_apply_simple_size_anim(p53)
                f_apply_simple_transparency_anim(p53)
                p53.Rate = 20
                p53.Texture = "http://www.roblox.com/asset/?id=4780023117"
            end;
            return v52;
        end)()))
        v_u_17:add_fevericon_for_id(13, ((function() --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v54 = v_u_5.FeverIconInfoBase:new()
            v54.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 294 ]]
                return "Kappa";
            end;
            v54.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 295 ]]
                return "http://www.roblox.com/asset/?id=4791574055";
            end;
            v54.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 296 ]]
                return "http://www.roblox.com/asset/?id=4780023489";
            end;
            v54.apply_to_emitter = function(_, p55) --[[ Name: apply_to_emitter ]] --[[ Line: 297 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p55)
                f_apply_simple_size_anim(p55)
                f_apply_simple_transparency_anim(p55)
                p55.Rate = 20
                p55.Texture = "http://www.roblox.com/asset/?id=4780023489"
            end;
            return v54;
        end)()))
        v_u_17:add_fevericon_for_id(14, ((function() --[[ Line: 306 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v56 = v_u_5.FeverIconInfoBase:new()
            v56.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 308 ]]
                return "Troll";
            end;
            v56.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 309 ]]
                return "http://www.roblox.com/asset/?id=4791574176";
            end;
            v56.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 310 ]]
                return "http://www.roblox.com/asset/?id=4780023803";
            end;
            v56.apply_to_emitter = function(_, p57) --[[ Name: apply_to_emitter ]] --[[ Line: 311 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p57)
                f_apply_simple_size_anim(p57)
                f_apply_simple_transparency_anim(p57)
                p57.Rate = 20
                p57.Texture = "http://www.roblox.com/asset/?id=4780023803"
            end;
            return v56;
        end)()))
        v_u_17:add_fevericon_for_id(15, ((function() --[[ Line: 320 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v58 = v_u_5.FeverIconInfoBase:new()
            v58.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 322 ]]
                return "Awesome";
            end;
            v58.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 323 ]]
                return "http://www.roblox.com/asset/?id=4791574270";
            end;
            v58.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 324 ]]
                return "http://www.roblox.com/asset/?id=4780027226";
            end;
            v58.apply_to_emitter = function(_, p59) --[[ Name: apply_to_emitter ]] --[[ Line: 325 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p59)
                f_apply_simple_size_anim(p59)
                f_apply_simple_transparency_anim(p59)
                p59.Rate = 20
                p59.Texture = "http://www.roblox.com/asset/?id=4780027226"
            end;
            return v58;
        end)()))
        v_u_17:add_fevericon_for_id(16, ((function() --[[ Line: 334 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v60 = v_u_5.FeverIconInfoBase:new()
            v60.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 336 ]]
                return "Tears";
            end;
            v60.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 337 ]]
                return "http://www.roblox.com/asset/?id=4791601156";
            end;
            v60.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 338 ]]
                return "http://www.roblox.com/asset/?id=4780027508";
            end;
            v60.apply_to_emitter = function(_, p61) --[[ Name: apply_to_emitter ]] --[[ Line: 339 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p61)
                f_apply_simple_size_anim(p61)
                f_apply_simple_transparency_anim(p61)
                p61.Rate = 20
                p61.Texture = "http://www.roblox.com/asset/?id=4780027508"
            end;
            return v60;
        end)()))
        v_u_17:add_fevericon_for_id(17, ((function() --[[ Line: 348 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v62 = v_u_5.FeverIconInfoBase:new()
            v62.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 350 ]]
                return "Forever Alone";
            end;
            v62.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 351 ]]
                return "http://www.roblox.com/asset/?id=4791574453";
            end;
            v62.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 352 ]]
                return "http://www.roblox.com/asset/?id=4780027950";
            end;
            v62.apply_to_emitter = function(_, p63) --[[ Name: apply_to_emitter ]] --[[ Line: 353 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p63)
                f_apply_simple_size_anim(p63)
                f_apply_simple_transparency_anim(p63)
                p63.Rate = 20
                p63.Texture = "http://www.roblox.com/asset/?id=4780027950"
            end;
            return v62;
        end)()))
        v_u_17:add_fevericon_for_id(18, ((function() --[[ Line: 362 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v64 = v_u_5.FeverIconInfoBase:new()
            v64.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 364 ]]
                return "Y U NO?";
            end;
            v64.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 365 ]]
                return "http://www.roblox.com/asset/?id=4791574583";
            end;
            v64.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 366 ]]
                return "http://www.roblox.com/asset/?id=4780028349";
            end;
            v64.apply_to_emitter = function(_, p65) --[[ Name: apply_to_emitter ]] --[[ Line: 367 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p65)
                f_apply_simple_size_anim(p65)
                f_apply_simple_transparency_anim(p65)
                p65.Rate = 20
                p65.Texture = "http://www.roblox.com/asset/?id=4780028349"
            end;
            return v64;
        end)()))
        v_u_17:add_fevericon_for_id(19, ((function() --[[ Line: 376 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v66 = v_u_5.FeverIconInfoBase:new()
            v66.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 378 ]]
                return "Doge";
            end;
            v66.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 379 ]]
                return "http://www.roblox.com/asset/?id=4791574678";
            end;
            v66.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 380 ]]
                return "http://www.roblox.com/asset/?id=4780028772";
            end;
            v66.apply_to_emitter = function(_, p67) --[[ Name: apply_to_emitter ]] --[[ Line: 381 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p67)
                f_apply_simple_size_anim(p67)
                f_apply_simple_transparency_anim(p67)
                p67.Rate = 20
                p67.Texture = "http://www.roblox.com/asset/?id=4780028772"
            end;
            return v66;
        end)()))
        v_u_17:add_fevericon_for_id(20, ((function() --[[ Line: 390 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v68 = v_u_5.FeverIconInfoBase:new()
            v68.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 392 ]]
                return "Thumbs Up";
            end;
            v68.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 393 ]]
                return "http://www.roblox.com/asset/?id=4791601317";
            end;
            v68.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 394 ]]
                return "http://www.roblox.com/asset/?id=4780426469";
            end;
            v68.apply_to_emitter = function(_, p69) --[[ Name: apply_to_emitter ]] --[[ Line: 395 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p69)
                f_apply_simple_size_anim(p69)
                f_apply_simple_transparency_anim(p69)
                p69.Rate = 20
                p69.Texture = "http://www.roblox.com/asset/?id=4780426469"
            end;
            return v68;
        end)()))
        v_u_17:add_fevericon_for_id(21, ((function() --[[ Line: 404 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v70 = v_u_5.FeverIconInfoBase:new()
            v70.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 406 ]]
                return "Awoo";
            end;
            v70.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 407 ]]
                return "http://www.roblox.com/asset/?id=4791574759";
            end;
            v70.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 408 ]]
                return "http://www.roblox.com/asset/?id=4780029156";
            end;
            v70.apply_to_emitter = function(_, p71) --[[ Name: apply_to_emitter ]] --[[ Line: 409 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p71)
                f_apply_simple_size_anim(p71)
                f_apply_simple_transparency_anim(p71)
                p71.Rate = 20
                p71.Texture = "http://www.roblox.com/asset/?id=4780029156"
            end;
            return v70;
        end)()))
        v_u_17:add_fevericon_for_id(22, ((function() --[[ Line: 418 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v72 = v_u_5.FeverIconInfoBase:new()
            v72.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 420 ]]
                return "Ora Ora";
            end;
            v72.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 421 ]]
                return "http://www.roblox.com/asset/?id=4791584898";
            end;
            v72.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 422 ]]
                return "http://www.roblox.com/asset/?id=4780029705";
            end;
            v72.apply_to_emitter = function(_, p73) --[[ Name: apply_to_emitter ]] --[[ Line: 423 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p73)
                f_apply_simple_size_anim(p73)
                f_apply_simple_transparency_anim(p73)
                p73.Rate = 20
                p73.Texture = "http://www.roblox.com/asset/?id=4780029705"
            end;
            return v72;
        end)()))
        v_u_17:add_fevericon_for_id(23, ((function() --[[ Line: 432 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v74 = v_u_5.FeverIconInfoBase:new()
            v74.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 434 ]]
                return "Walter";
            end;
            v74.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 435 ]]
                return "http://www.roblox.com/asset/?id=4791574930";
            end;
            v74.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 436 ]]
                return "http://www.roblox.com/asset/?id=4780030137";
            end;
            v74.apply_to_emitter = function(_, p75) --[[ Name: apply_to_emitter ]] --[[ Line: 437 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p75)
                f_apply_simple_size_anim(p75)
                f_apply_simple_transparency_anim(p75)
                p75.Rate = 20
                p75.Texture = "http://www.roblox.com/asset/?id=4780030137"
            end;
            return v74;
        end)()))
        v_u_17:add_fevericon_for_id(24, ((function() --[[ Line: 446 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v76 = v_u_5.FeverIconInfoBase:new()
            v76.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 448 ]]
                return "Clown";
            end;
            v76.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 449 ]]
                return "http://www.roblox.com/asset/?id=4791575012";
            end;
            v76.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 450 ]]
                return "http://www.roblox.com/asset/?id=4780031534";
            end;
            v76.apply_to_emitter = function(_, p77) --[[ Name: apply_to_emitter ]] --[[ Line: 451 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p77)
                f_apply_simple_size_anim(p77)
                f_apply_simple_transparency_anim(p77)
                p77.Rate = 20
                p77.Texture = "http://www.roblox.com/asset/?id=4780031534"
            end;
            return v76;
        end)()))
        v_u_17:add_fevericon_for_id(25, ((function() --[[ Line: 460 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v78 = v_u_5.FeverIconInfoBase:new()
            v78.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 462 ]]
                return "Robeats";
            end;
            v78.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 463 ]]
                return "rbxassetid://15247740594";
            end;
            v78.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 464 ]]
                return "rbxassetid://15247740484";
            end;
            v78.apply_to_emitter = function(_, p79) --[[ Name: apply_to_emitter ]] --[[ Line: 465 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p79)
                f_apply_simple_size_anim(p79)
                f_apply_simple_transparency_anim(p79)
                p79.Rate = 20
                p79.Texture = "rbxassetid://15247740484"
            end;
            return v78;
        end)()))
        v_u_17:add_fevericon_for_id(26, ((function() --[[ Line: 474 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v80 = v_u_5.FeverIconInfoBase:new()
            v80.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 476 ]]
                return "Wheelchair Gang";
            end;
            v80.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 477 ]]
                return "http://www.roblox.com/asset/?id=4791589096";
            end;
            v80.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 478 ]]
                return "http://www.roblox.com/asset/?id=4780033734";
            end;
            v80.apply_to_emitter = function(_, p81) --[[ Name: apply_to_emitter ]] --[[ Line: 479 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p81)
                f_apply_simple_size_anim(p81)
                f_apply_simple_transparency_anim(p81)
                p81.Rate = 20
                p81.Texture = "http://www.roblox.com/asset/?id=4780033734"
            end;
            return v80;
        end)()))
        v_u_17:add_fevericon_for_id(27, ((function() --[[ Line: 488 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v82 = v_u_5.FeverIconInfoBase:new()
            v82.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 490 ]]
                return "Penguin";
            end;
            v82.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 491 ]]
                return "http://www.roblox.com/asset/?id=4791575283";
            end;
            v82.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 492 ]]
                return "http://www.roblox.com/asset/?id=4780034142";
            end;
            v82.apply_to_emitter = function(_, p83) --[[ Name: apply_to_emitter ]] --[[ Line: 493 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p83)
                f_apply_simple_size_anim(p83)
                f_apply_simple_transparency_anim(p83)
                p83.Rate = 20
                p83.Texture = "http://www.roblox.com/asset/?id=4780034142"
            end;
            return v82;
        end)()))
        v_u_17:add_fevericon_for_id(28, ((function() --[[ Line: 502 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v84 = v_u_5.FeverIconInfoBase:new()
            v84.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 504 ]]
                return "Thinking";
            end;
            v84.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 505 ]]
                return "http://www.roblox.com/asset/?id=4791575348";
            end;
            v84.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 506 ]]
                return "http://www.roblox.com/asset/?id=4780071845";
            end;
            v84.apply_to_emitter = function(_, p85) --[[ Name: apply_to_emitter ]] --[[ Line: 507 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p85)
                f_apply_simple_size_anim(p85)
                f_apply_simple_transparency_anim(p85)
                p85.Rate = 20
                p85.Texture = "http://www.roblox.com/asset/?id=4780071845"
            end;
            return v84;
        end)()))
        v_u_17:add_fevericon_for_id(29, ((function() --[[ Line: 516 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v86 = v_u_5.FeverIconInfoBase:new()
            v86.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 518 ]]
                return "Soy";
            end;
            v86.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 519 ]]
                return "rbxassetid://15100046955";
            end;
            v86.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 520 ]]
                return "rbxassetid://15100046897";
            end;
            v86.apply_to_emitter = function(_, p87) --[[ Name: apply_to_emitter ]] --[[ Line: 521 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p87)
                f_apply_simple_size_anim(p87)
                f_apply_simple_transparency_anim(p87)
                p87.Rate = 20
                p87.Texture = "http://www.roblox.com/asset/?id=15100046897"
            end;
            return v86;
        end)()))
        v_u_17:add_fevericon_for_id(30, ((function() --[[ Line: 530 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v88 = v_u_5.FeverIconInfoBase:new()
            v88.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 532 ]]
                return "scoobis";
            end;
            v88.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 533 ]]
                return "http://www.roblox.com/asset/?id=4791575518";
            end;
            v88.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 534 ]]
                return "http://www.roblox.com/asset/?id=4780074047";
            end;
            v88.apply_to_emitter = function(_, p89) --[[ Name: apply_to_emitter ]] --[[ Line: 535 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p89)
                f_apply_simple_size_anim(p89)
                f_apply_simple_transparency_anim(p89)
                p89.Rate = 20
                p89.Texture = "http://www.roblox.com/asset/?id=4780074047"
            end;
            return v88;
        end)()))
        v_u_17:add_fevericon_for_id(31, ((function() --[[ Line: 544 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v90 = v_u_5.FeverIconInfoBase:new()
            v90.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 546 ]]
                return "Man Face";
            end;
            v90.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 547 ]]
                return "http://www.roblox.com/asset/?id=4791575608";
            end;
            v90.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 548 ]]
                return "http://www.roblox.com/asset/?id=4780074424";
            end;
            v90.apply_to_emitter = function(_, p91) --[[ Name: apply_to_emitter ]] --[[ Line: 549 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p91)
                f_apply_simple_size_anim(p91)
                f_apply_simple_transparency_anim(p91)
                p91.Rate = 20
                p91.Texture = "http://www.roblox.com/asset/?id=4780074424"
            end;
            return v90;
        end)()))
        v_u_17:add_fevericon_for_id(32, ((function() --[[ Line: 558 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v92 = v_u_5.FeverIconInfoBase:new()
            v92.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 560 ]]
                return "Philosoraptor";
            end;
            v92.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 561 ]]
                return "rbxassetid://15100122836";
            end;
            v92.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 562 ]]
                return "rbxassetid://15100122891";
            end;
            v92.apply_to_emitter = function(_, p93) --[[ Name: apply_to_emitter ]] --[[ Line: 563 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p93)
                f_apply_simple_size_anim(p93)
                f_apply_simple_transparency_anim(p93)
                p93.Rate = 20
                p93.Texture = "http://www.roblox.com/asset/?id=15100122891"
            end;
            return v92;
        end)()))
        v_u_17:add_fevericon_for_id(33, ((function() --[[ Line: 572 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v94 = v_u_5.FeverIconInfoBase:new()
            v94.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 574 ]]
                return "Roblox";
            end;
            v94.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 575 ]]
                return "http://www.roblox.com/asset/?id=4791601021";
            end;
            v94.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 576 ]]
                return "http://www.roblox.com/asset/?id=4780075235";
            end;
            v94.apply_to_emitter = function(_, p95) --[[ Name: apply_to_emitter ]] --[[ Line: 577 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p95)
                f_apply_simple_size_anim(p95)
                f_apply_simple_transparency_anim(p95)
                p95.Rate = 20
                p95.Texture = "http://www.roblox.com/asset/?id=4780075235"
            end;
            return v94;
        end)()))
        v_u_17:add_fevericon_for_id(34, ((function() --[[ Line: 587 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v96 = v_u_5.FeverIconInfoBase:new()
            v96.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 589 ]]
                return "Zara";
            end;
            v96.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 590 ]]
                return "rbxassetid://7423373126";
            end;
            v96.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 591 ]]
                return "rbxassetid://7423375239";
            end;
            v96.apply_to_emitter = function(p97, p98) --[[ Name: apply_to_emitter ]] --[[ Line: 592 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p98)
                f_apply_simple_size_anim(p98)
                f_apply_simple_transparency_anim(p98)
                p98.Rate = 20
                p98.Texture = p97:get_image()
            end;
            return v96;
        end)()))
        v_u_17:add_fevericon_for_id(35, ((function() --[[ Line: 601 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v99 = v_u_5.FeverIconInfoBase:new()
            v99.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 603 ]]
                return "Starlet";
            end;
            v99.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 604 ]]
                return "rbxassetid://7423373230";
            end;
            v99.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 605 ]]
                return "rbxassetid://7423375381";
            end;
            v99.apply_to_emitter = function(p100, p101) --[[ Name: apply_to_emitter ]] --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p101)
                f_apply_simple_size_anim(p101)
                f_apply_simple_transparency_anim(p101)
                p101.Rate = 20
                p101.Texture = p100:get_image()
            end;
            return v99;
        end)()))
        v_u_17:add_fevericon_for_id(36, ((function() --[[ Line: 615 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v102 = v_u_5.FeverIconInfoBase:new()
            v102.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 617 ]]
                return "StaringCat";
            end;
            v102.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 618 ]]
                return "rbxassetid://7423373342";
            end;
            v102.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 619 ]]
                return "rbxassetid://7423375470";
            end;
            v102.apply_to_emitter = function(p103, p104) --[[ Name: apply_to_emitter ]] --[[ Line: 620 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p104)
                f_apply_simple_size_anim(p104)
                f_apply_simple_transparency_anim(p104)
                p104.Rate = 20
                p104.Texture = p103:get_image()
            end;
            return v102;
        end)()))
        v_u_17:add_fevericon_for_id(37, ((function() --[[ Line: 629 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v105 = v_u_5.FeverIconInfoBase:new()
            v105.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 631 ]]
                return "StarMachine";
            end;
            v105.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 632 ]]
                return "rbxassetid://7423373417";
            end;
            v105.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 633 ]]
                return "rbxassetid://7423375612";
            end;
            v105.apply_to_emitter = function(p106, p107) --[[ Name: apply_to_emitter ]] --[[ Line: 634 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p107)
                f_apply_simple_size_anim(p107)
                f_apply_simple_transparency_anim(p107)
                p107.Rate = 20
                p107.Texture = p106:get_image()
            end;
            return v105;
        end)()))
        v_u_17:add_fevericon_for_id(38, ((function() --[[ Line: 643 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v108 = v_u_5.FeverIconInfoBase:new()
            v108.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 645 ]]
                return "Silentroom";
            end;
            v108.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 646 ]]
                return "rbxassetid://7423373515";
            end;
            v108.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 647 ]]
                return "rbxassetid://7423375746";
            end;
            v108.apply_to_emitter = function(p109, p110) --[[ Name: apply_to_emitter ]] --[[ Line: 648 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p110)
                f_apply_simple_size_anim(p110)
                f_apply_simple_transparency_anim(p110)
                p110.Rate = 20
                p110.Texture = p109:get_image()
            end;
            return v108;
        end)()))
        v_u_17:add_fevericon_for_id(39, ((function() --[[ Line: 657 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v111 = v_u_5.FeverIconInfoBase:new()
            v111.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 659 ]]
                return "Se-U-Ra";
            end;
            v111.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 660 ]]
                return "rbxassetid://8186575316";
            end;
            v111.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 661 ]]
                return "rbxassetid://8186575425";
            end;
            v111.apply_to_emitter = function(p112, p113) --[[ Name: apply_to_emitter ]] --[[ Line: 662 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p113)
                f_apply_simple_size_anim(p113)
                f_apply_simple_transparency_anim(p113)
                p113.Rate = 20
                p113.Texture = p112:get_image()
            end;
            return v111;
        end)()))
        v_u_17:add_fevericon_for_id(40, ((function() --[[ Line: 671 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v114 = v_u_5.FeverIconInfoBase:new()
            v114.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 673 ]]
                return "Roxie";
            end;
            v114.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 674 ]]
                return "rbxassetid://7423373740";
            end;
            v114.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 675 ]]
                return "rbxassetid://7423375976";
            end;
            v114.apply_to_emitter = function(p115, p116) --[[ Name: apply_to_emitter ]] --[[ Line: 676 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p116)
                f_apply_simple_size_anim(p116)
                f_apply_simple_transparency_anim(p116)
                p116.Rate = 20
                p116.Texture = p115:get_image()
            end;
            return v114;
        end)()))
        v_u_17:add_fevericon_for_id(41, ((function() --[[ Line: 685 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v117 = v_u_5.FeverIconInfoBase:new()
            v117.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 687 ]]
                return "Note Machine";
            end;
            v117.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 688 ]]
                return "rbxassetid://7423373843";
            end;
            v117.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 689 ]]
                return "rbxassetid://7423376124";
            end;
            v117.apply_to_emitter = function(p118, p119) --[[ Name: apply_to_emitter ]] --[[ Line: 690 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p119)
                f_apply_simple_size_anim(p119)
                f_apply_simple_transparency_anim(p119)
                p119.Rate = 20
                p119.Texture = p118:get_image()
            end;
            return v117;
        end)()))
        v_u_17:add_fevericon_for_id(42, ((function() --[[ Line: 699 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v120 = v_u_5.FeverIconInfoBase:new()
            v120.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 701 ]]
                return "Monstercat";
            end;
            v120.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 702 ]]
                return "rbxassetid://8837850230";
            end;
            v120.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 703 ]]
                return "rbxassetid://7423376285";
            end;
            v120.apply_to_emitter = function(p121, p122) --[[ Name: apply_to_emitter ]] --[[ Line: 704 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p122)
                f_apply_simple_size_anim(p122)
                f_apply_simple_transparency_anim(p122)
                p122.Rate = 20
                p122.Texture = p121:get_image()
            end;
            return v120;
        end)()))
        v_u_17:add_fevericon_for_id(43, ((function() --[[ Line: 713 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v123 = v_u_5.FeverIconInfoBase:new()
            v123.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 715 ]]
                return "Mattie";
            end;
            v123.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 716 ]]
                return "rbxassetid://7423374046";
            end;
            v123.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 717 ]]
                return "rbxassetid://7423376441";
            end;
            v123.apply_to_emitter = function(p124, p125) --[[ Name: apply_to_emitter ]] --[[ Line: 718 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p125)
                f_apply_simple_size_anim(p125)
                f_apply_simple_transparency_anim(p125)
                p125.Rate = 20
                p125.Texture = p124:get_image()
            end;
            return v123;
        end)()))
        v_u_17:add_fevericon_for_id(44, ((function() --[[ Line: 727 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v126 = v_u_5.FeverIconInfoBase:new()
            v126.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 729 ]]
                return "Marsha";
            end;
            v126.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 730 ]]
                return "rbxassetid://7423374159";
            end;
            v126.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 731 ]]
                return "rbxassetid://7423376579";
            end;
            v126.apply_to_emitter = function(p127, p128) --[[ Name: apply_to_emitter ]] --[[ Line: 732 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p128)
                f_apply_simple_size_anim(p128)
                f_apply_simple_transparency_anim(p128)
                p128.Rate = 20
                p128.Texture = p127:get_image()
            end;
            return v126;
        end)()))
        v_u_17:add_fevericon_for_id(45, ((function() --[[ Line: 741 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v129 = v_u_5.FeverIconInfoBase:new()
            v129.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 743 ]]
                return "Lisa";
            end;
            v129.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 744 ]]
                return "rbxassetid://7423374287";
            end;
            v129.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 745 ]]
                return "rbxassetid://7423376733";
            end;
            v129.apply_to_emitter = function(p130, p131) --[[ Name: apply_to_emitter ]] --[[ Line: 746 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p131)
                f_apply_simple_size_anim(p131)
                f_apply_simple_transparency_anim(p131)
                p131.Rate = 20
                p131.Texture = p130:get_image()
            end;
            return v129;
        end)()))
        v_u_17:add_fevericon_for_id(46, ((function() --[[ Line: 755 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v132 = v_u_5.FeverIconInfoBase:new()
            v132.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 757 ]]
                return "Interesting";
            end;
            v132.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 758 ]]
                return "rbxassetid://7423374375";
            end;
            v132.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 759 ]]
                return "rbxassetid://7423376844";
            end;
            v132.apply_to_emitter = function(p133, p134) --[[ Name: apply_to_emitter ]] --[[ Line: 760 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p134)
                f_apply_simple_size_anim(p134)
                f_apply_simple_transparency_anim(p134)
                p134.Rate = 20
                p134.Texture = p133:get_image()
            end;
            return v132;
        end)()))
        v_u_17:add_fevericon_for_id(47, ((function() --[[ Line: 769 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v135 = v_u_5.FeverIconInfoBase:new()
            v135.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 771 ]]
                return "Friendly Alien";
            end;
            v135.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 772 ]]
                return "rbxassetid://7423374518";
            end;
            v135.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 773 ]]
                return "rbxassetid://7423376971";
            end;
            v135.apply_to_emitter = function(p136, p137) --[[ Name: apply_to_emitter ]] --[[ Line: 774 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p137)
                f_apply_simple_size_anim(p137)
                f_apply_simple_transparency_anim(p137)
                p137.Rate = 20
                p137.Texture = p136:get_image()
            end;
            return v135;
        end)()))
        v_u_17:add_fevericon_for_id(48, ((function() --[[ Line: 783 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v138 = v_u_5.FeverIconInfoBase:new()
            v138.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 785 ]]
                return "Despacito Spider";
            end;
            v138.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 786 ]]
                return "rbxassetid://7423374660";
            end;
            v138.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 787 ]]
                return "rbxassetid://7423377060";
            end;
            v138.apply_to_emitter = function(p139, p140) --[[ Name: apply_to_emitter ]] --[[ Line: 788 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p140)
                f_apply_simple_size_anim(p140)
                f_apply_simple_transparency_anim(p140)
                p140.Rate = 20
                p140.Texture = p139:get_image()
            end;
            return v138;
        end)()))
        v_u_17:add_fevericon_for_id(49, ((function() --[[ Line: 797 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v141 = v_u_5.FeverIconInfoBase:new()
            v141.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 799 ]]
                return "Cool Shades";
            end;
            v141.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 800 ]]
                return "rbxassetid://7423374772";
            end;
            v141.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 801 ]]
                return "rbxassetid://7423377150";
            end;
            v141.apply_to_emitter = function(p142, p143) --[[ Name: apply_to_emitter ]] --[[ Line: 802 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p143)
                f_apply_simple_size_anim(p143)
                f_apply_simple_transparency_anim(p143)
                p143.Rate = 20
                p143.Texture = p142:get_image()
            end;
            return v141;
        end)()))
        v_u_17:add_fevericon_for_id(50, ((function() --[[ Line: 811 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v144 = v_u_5.FeverIconInfoBase:new()
            v144.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 813 ]]
                return "Chroma";
            end;
            v144.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 814 ]]
                return "rbxassetid://7423374894";
            end;
            v144.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 815 ]]
                return "rbxassetid://7423377242";
            end;
            v144.apply_to_emitter = function(p145, p146) --[[ Name: apply_to_emitter ]] --[[ Line: 816 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p146)
                f_apply_simple_size_anim(p146)
                f_apply_simple_transparency_anim(p146)
                p146.Rate = 20
                p146.Texture = p145:get_image()
            end;
            return v144;
        end)()))
        v_u_17:add_fevericon_for_id(51, ((function() --[[ Line: 825 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v147 = v_u_5.FeverIconInfoBase:new()
            v147.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 827 ]]
                return "Cametek";
            end;
            v147.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 828 ]]
                return "http://www.roblox.com/asset/?id=7449970847";
            end;
            v147.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 829 ]]
                return "http://www.roblox.com/asset/?id=7449969763";
            end;
            v147.apply_to_emitter = function(p148, p149) --[[ Name: apply_to_emitter ]] --[[ Line: 830 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p149)
                f_apply_simple_size_anim(p149)
                f_apply_simple_transparency_anim(p149)
                p149.Rate = 20
                p149.Texture = p148:get_image()
            end;
            return v147;
        end)()))
        v_u_17:add_fevericon_for_id(52, ((function() --[[ Line: 839 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v150 = v_u_5.FeverIconInfoBase:new()
            v150.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 841 ]]
                return "ARForest";
            end;
            v150.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 842 ]]
                return "rbxassetid://7423375107";
            end;
            v150.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 843 ]]
                return "rbxassetid://7423377548";
            end;
            v150.apply_to_emitter = function(p151, p152) --[[ Name: apply_to_emitter ]] --[[ Line: 844 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p152)
                f_apply_simple_size_anim(p152)
                f_apply_simple_transparency_anim(p152)
                p152.Rate = 20
                p152.Texture = p151:get_image()
            end;
            return v150;
        end)()))
        v_u_17:add_fevericon_for_id(53, ((function() --[[ Line: 853 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v153 = v_u_5.FeverIconInfoBase:new()
            v153.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 855 ]]
                return "FNF Boyfriend";
            end;
            v153.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 856 ]]
                return "http://www.roblox.com/asset/?id=7449657698";
            end;
            v153.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 857 ]]
                return "http://www.roblox.com/asset/?id=7449656847";
            end;
            v153.apply_to_emitter = function(p154, p155) --[[ Name: apply_to_emitter ]] --[[ Line: 858 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p155)
                f_apply_simple_size_anim(p155)
                f_apply_simple_transparency_anim(p155)
                p155.Rate = 20
                p155.Texture = p154:get_image()
            end;
            return v153;
        end)()))
        v_u_17:add_fevericon_for_id(54, ((function() --[[ Line: 867 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v156 = v_u_5.FeverIconInfoBase:new()
            v156.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 869 ]]
                return "Poppy";
            end;
            v156.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 870 ]]
                return "http://www.roblox.com/asset/?id=7528187529";
            end;
            v156.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 871 ]]
                return "http://www.roblox.com/asset/?id=7528187141";
            end;
            v156.apply_to_emitter = function(p157, p158) --[[ Name: apply_to_emitter ]] --[[ Line: 872 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p158)
                f_apply_simple_size_anim(p158)
                f_apply_simple_transparency_anim(p158)
                p158.Rate = 20
                p158.Texture = p157:get_image()
            end;
            return v156;
        end)()))
        v_u_17:add_fevericon_for_id(55, ((function() --[[ Line: 881 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v159 = v_u_5.FeverIconInfoBase:new()
            v159.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 883 ]]
                return "garlagan";
            end;
            v159.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 884 ]]
                return "http://www.roblox.com/asset/?id=7547707339";
            end;
            v159.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 885 ]]
                return "http://www.roblox.com/asset/?id=7547707871";
            end;
            v159.apply_to_emitter = function(p160, p161) --[[ Name: apply_to_emitter ]] --[[ Line: 886 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p161)
                f_apply_simple_size_anim(p161)
                f_apply_simple_transparency_anim(p161)
                p161.Rate = 20
                p161.Texture = p160:get_image()
            end;
            return v159;
        end)()))
        v_u_17:add_fevericon_for_id(56, ((function() --[[ Line: 895 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v162 = v_u_5.FeverIconInfoBase:new()
            v162.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 897 ]]
                return "naruto2413";
            end;
            v162.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 898 ]]
                return "http://www.roblox.com/asset/?id=7676765988";
            end;
            v162.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 899 ]]
                return "http://www.roblox.com/asset/?id=7676766574";
            end;
            v162.apply_to_emitter = function(p163, p164) --[[ Name: apply_to_emitter ]] --[[ Line: 900 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p164)
                f_apply_simple_size_anim(p164)
                f_apply_simple_transparency_anim(p164)
                p164.Rate = 20
                p164.Texture = p163:get_image()
            end;
            return v162;
        end)()))
        v_u_17:add_fevericon_for_id(57, ((function() --[[ Line: 909 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v165 = v_u_5.FeverIconInfoBase:new()
            v165.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 911 ]]
                return "Creo";
            end;
            v165.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 912 ]]
                return "http://www.roblox.com/asset/?id=7739768551";
            end;
            v165.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 913 ]]
                return "http://www.roblox.com/asset/?id=7739768148";
            end;
            v165.apply_to_emitter = function(p166, p167) --[[ Name: apply_to_emitter ]] --[[ Line: 914 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p167)
                f_apply_simple_size_anim(p167)
                f_apply_simple_transparency_anim(p167)
                p167.Rate = 20
                p167.Texture = p166:get_image()
            end;
            return v165;
        end)()))
        v_u_17:add_fevericon_for_id(58, ((function() --[[ Line: 923 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v168 = v_u_5.FeverIconInfoBase:new()
            v168.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 925 ]]
                return "Pumpkin Head";
            end;
            v168.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 926 ]]
                return "http://www.roblox.com/asset/?id=7792348842";
            end;
            v168.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 927 ]]
                return "http://www.roblox.com/asset/?id=7792348481";
            end;
            v168.apply_to_emitter = function(p169, p170) --[[ Name: apply_to_emitter ]] --[[ Line: 928 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p170)
                f_apply_simple_size_anim(p170)
                f_apply_simple_transparency_anim(p170)
                p170.Rate = 20
                p170.Texture = p169:get_image()
            end;
            return v168;
        end)()))
        v_u_17:add_fevericon_for_id(59, ((function() --[[ Line: 937 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v171 = v_u_5.FeverIconInfoBase:new()
            v171.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 939 ]]
                return "xi";
            end;
            v171.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 940 ]]
                return "rbxassetid://7903071807";
            end;
            v171.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 941 ]]
                return "rbxassetid://7903066620";
            end;
            v171.apply_to_emitter = function(p172, p173) --[[ Name: apply_to_emitter ]] --[[ Line: 942 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p173)
                f_apply_simple_size_anim(p173)
                f_apply_simple_transparency_anim(p173)
                p173.Rate = 20
                p173.Texture = p172:get_image()
            end;
            return v171;
        end)()))
        v_u_17:add_fevericon_for_id(60, ((function() --[[ Line: 951 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v174 = v_u_5.FeverIconInfoBase:new()
            v174.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 953 ]]
                return "James Landino";
            end;
            v174.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 954 ]]
                return "rbxassetid://7962391896";
            end;
            v174.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 955 ]]
                return "rbxassetid://7962389205";
            end;
            v174.apply_to_emitter = function(p175, p176) --[[ Name: apply_to_emitter ]] --[[ Line: 956 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p176)
                f_apply_simple_size_anim(p176)
                f_apply_simple_transparency_anim(p176)
                p176.Rate = 20
                p176.Texture = p175:get_image()
            end;
            return v174;
        end)()))
        v_u_17:add_fevericon_for_id(61, ((function() --[[ Line: 965 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v177 = v_u_5.FeverIconInfoBase:new()
            v177.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 967 ]]
                return "F-777 Phantom";
            end;
            v177.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 968 ]]
                return "rbxassetid://8037221222";
            end;
            v177.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 969 ]]
                return "rbxassetid://8037221347";
            end;
            v177.apply_to_emitter = function(p178, p179) --[[ Name: apply_to_emitter ]] --[[ Line: 970 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p179)
                f_apply_simple_size_anim(p179)
                f_apply_simple_transparency_anim(p179)
                p179.Rate = 20
                p179.Texture = p178:get_image()
            end;
            return v177;
        end)()))
        v_u_17:add_fevericon_for_id(62, ((function() --[[ Line: 979 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v180 = v_u_5.FeverIconInfoBase:new()
            v180.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 981 ]]
                return "Just Dance 2022";
            end;
            v180.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 982 ]]
                return "rbxassetid://8076636187";
            end;
            v180.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 983 ]]
                return "rbxassetid://8076636270";
            end;
            v180.apply_to_emitter = function(p181, p182) --[[ Name: apply_to_emitter ]] --[[ Line: 984 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p182)
                f_apply_simple_size_anim(p182)
                f_apply_simple_transparency_anim(p182)
                p182.Rate = 20
                p182.Texture = p181:get_image()
            end;
            return v180;
        end)()))
        v_u_17:add_fevericon_for_id(63, ((function() --[[ Line: 993 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v183 = v_u_5.FeverIconInfoBase:new()
            v183.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 995 ]]
                return "dark cat";
            end;
            v183.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 996 ]]
                return "rbxassetid://8201687162";
            end;
            v183.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 997 ]]
                return "rbxassetid://8201687202";
            end;
            v183.apply_to_emitter = function(p184, p185) --[[ Name: apply_to_emitter ]] --[[ Line: 998 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p185)
                f_apply_simple_size_anim(p185)
                f_apply_simple_transparency_anim(p185)
                p185.Rate = 20
                p185.Texture = p184:get_image()
            end;
            return v183;
        end)()))
        v_u_17:add_fevericon_for_id(64, ((function() --[[ Line: 1007 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v186 = v_u_5.FeverIconInfoBase:new()
            v186.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1009 ]]
                return "Santa";
            end;
            v186.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1010 ]]
                return "rbxassetid://8275110678";
            end;
            v186.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1011 ]]
                return "rbxassetid://8275110814";
            end;
            v186.apply_to_emitter = function(p187, p188) --[[ Name: apply_to_emitter ]] --[[ Line: 1012 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p188)
                f_apply_simple_size_anim(p188)
                f_apply_simple_transparency_anim(p188)
                p188.Rate = 20
                p188.Texture = p187:get_image()
            end;
            return v186;
        end)()))
        v_u_17:add_fevericon_for_id(65, ((function() --[[ Line: 1021 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v189 = v_u_5.FeverIconInfoBase:new()
            v189.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1023 ]]
                return "Winter Marsha";
            end;
            v189.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1024 ]]
                return "rbxassetid://8319856945";
            end;
            v189.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1025 ]]
                return "rbxassetid://8319856778";
            end;
            v189.apply_to_emitter = function(p190, p191) --[[ Name: apply_to_emitter ]] --[[ Line: 1026 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p191)
                f_apply_simple_size_anim(p191)
                f_apply_simple_transparency_anim(p191)
                p191.Rate = 20
                p191.Texture = p190:get_image()
            end;
            return v189;
        end)()))
        v_u_17:add_fevericon_for_id(66, ((function() --[[ Line: 1035 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v192 = v_u_5.FeverIconInfoBase:new()
            v192.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1037 ]]
                return "Tobu";
            end;
            v192.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1038 ]]
                return "rbxassetid://8837839068";
            end;
            v192.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1039 ]]
                return "rbxassetid://8401605626";
            end;
            v192.apply_to_emitter = function(p193, p194) --[[ Name: apply_to_emitter ]] --[[ Line: 1040 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p194)
                f_apply_simple_size_anim(p194)
                f_apply_simple_transparency_anim(p194)
                p194.Rate = 20
                p194.Texture = p193:get_image()
            end;
            return v192;
        end)()))
        v_u_17:add_fevericon_for_id(67, ((function() --[[ Line: 1049 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v195 = v_u_5.FeverIconInfoBase:new()
            v195.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1051 ]]
                return "Atsuover";
            end;
            v195.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1052 ]]
                return "rbxassetid://8511327660";
            end;
            v195.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1053 ]]
                return "rbxassetid://8511327738";
            end;
            v195.apply_to_emitter = function(p196, p197) --[[ Name: apply_to_emitter ]] --[[ Line: 1054 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p197)
                f_apply_simple_size_anim(p197)
                f_apply_simple_transparency_anim(p197)
                p197.Rate = 20
                p197.Texture = p196:get_image()
            end;
            return v195;
        end)()))
        v_u_17:add_fevericon_for_id(68, ((function() --[[ Line: 1063 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v198 = v_u_5.FeverIconInfoBase:new()
            v198.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1065 ]]
                return "KepoShrug";
            end;
            v198.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1066 ]]
                return "rbxassetid://8581932549";
            end;
            v198.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1067 ]]
                return "rbxassetid://8581932683";
            end;
            v198.apply_to_emitter = function(p199, p200) --[[ Name: apply_to_emitter ]] --[[ Line: 1068 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p200)
                f_apply_simple_size_anim(p200)
                f_apply_simple_transparency_anim(p200)
                p200.Rate = 20
                p200.Texture = p199:get_image()
            end;
            return v198;
        end)()))
        v_u_17:add_fevericon_for_id(69, ((function() --[[ Line: 1077 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v201 = v_u_5.FeverIconInfoBase:new()
            v201.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1079 ]]
                return "Slynk";
            end;
            v201.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1080 ]]
                return "rbxassetid://8644541978";
            end;
            v201.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1081 ]]
                return "rbxassetid://8644542054";
            end;
            v201.apply_to_emitter = function(p202, p203) --[[ Name: apply_to_emitter ]] --[[ Line: 1082 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p203)
                f_apply_simple_size_anim(p203)
                f_apply_simple_transparency_anim(p203)
                p203.Rate = 20
                p203.Texture = p202:get_image()
            end;
            return v201;
        end)()))
        v_u_17:add_fevericon_for_id(70, ((function() --[[ Line: 1091 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v204 = v_u_5.FeverIconInfoBase:new()
            v204.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1093 ]]
                return "Similar Outskirts";
            end;
            v204.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1094 ]]
                return "rbxassetid://8837883544";
            end;
            v204.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1095 ]]
                return "rbxassetid://8837883643";
            end;
            v204.apply_to_emitter = function(p205, p206) --[[ Name: apply_to_emitter ]] --[[ Line: 1096 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p206)
                f_apply_simple_size_anim(p206)
                f_apply_simple_transparency_anim(p206)
                p206.Rate = 20
                p206.Texture = p205:get_image()
            end;
            return v204;
        end)()))
        v_u_17:add_fevericon_for_id(71, ((function() --[[ Line: 1105 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v207 = v_u_5.FeverIconInfoBase:new()
            v207.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1107 ]]
                return "MisoilePunch (MisomyL)";
            end;
            v207.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1108 ]]
                return "rbxassetid://8919429219";
            end;
            v207.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1109 ]]
                return "rbxassetid://8919429427";
            end;
            v207.apply_to_emitter = function(p208, p209) --[[ Name: apply_to_emitter ]] --[[ Line: 1110 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p209)
                f_apply_simple_size_anim(p209)
                f_apply_simple_transparency_anim(p209)
                p209.Rate = 20
                p209.Texture = p208:get_image()
            end;
            return v207;
        end)()))
        v_u_17:add_fevericon_for_id(72, ((function() --[[ Line: 1119 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v210 = v_u_5.FeverIconInfoBase:new()
            v210.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1121 ]]
                return "MisoilePunch (Ponchi)";
            end;
            v210.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1122 ]]
                return "rbxassetid://8919429036";
            end;
            v210.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1123 ]]
                return "rbxassetid://8919429328";
            end;
            v210.apply_to_emitter = function(p211, p212) --[[ Name: apply_to_emitter ]] --[[ Line: 1124 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p212)
                f_apply_simple_size_anim(p212)
                f_apply_simple_transparency_anim(p212)
                p212.Rate = 20
                p212.Texture = p211:get_image()
            end;
            return v210;
        end)()))
        v_u_17:add_fevericon_for_id(73, ((function() --[[ Line: 1133 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v213 = v_u_5.FeverIconInfoBase:new()
            v213.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1135 ]]
                return "Waterflame";
            end;
            v213.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1136 ]]
                return "rbxassetid://9042831351";
            end;
            v213.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1137 ]]
                return "http://www.roblox.com/asset/?id=9082984815";
            end;
            v213.apply_to_emitter = function(p214, p215) --[[ Name: apply_to_emitter ]] --[[ Line: 1138 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p215)
                f_apply_simple_size_anim(p215)
                f_apply_simple_transparency_anim(p215)
                p215.Rate = 20
                p215.Texture = p214:get_image()
            end;
            return v213;
        end)()))
        v_u_17:add_fevericon_for_id(74, ((function() --[[ Line: 1147 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v216 = v_u_5.FeverIconInfoBase:new()
            v216.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1149 ]]
                return "Mini Alien";
            end;
            v216.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1150 ]]
                return "rbxassetid://9051230392";
            end;
            v216.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1151 ]]
                return "rbxassetid://9051230495";
            end;
            v216.apply_to_emitter = function(p217, p218) --[[ Name: apply_to_emitter ]] --[[ Line: 1152 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p218)
                f_apply_simple_size_anim(p218)
                f_apply_simple_transparency_anim(p218)
                p218.Rate = 20
                p218.Texture = p217:get_image()
            end;
            return v216;
        end)()))
        v_u_17:add_fevericon_for_id(75, ((function() --[[ Line: 1161 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v219 = v_u_5.FeverIconInfoBase:new()
            v219.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1163 ]]
                return "Armageddon (LeaF)";
            end;
            v219.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1164 ]]
                return "rbxassetid://9106287883";
            end;
            v219.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1165 ]]
                return "rbxassetid://9106287951";
            end;
            v219.apply_to_emitter = function(p220, p221) --[[ Name: apply_to_emitter ]] --[[ Line: 1166 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p221)
                f_apply_simple_size_anim(p221)
                f_apply_simple_transparency_anim(p221)
                p221.Rate = 20
                p221.Texture = p220:get_image()
            end;
            return v219;
        end)()))
        v_u_17:add_fevericon_for_id(76, ((function() --[[ Line: 1175 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v222 = v_u_5.FeverIconInfoBase:new()
            v222.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1177 ]]
                return "Hyper Potions";
            end;
            v222.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1178 ]]
                return "rbxassetid://9181110027";
            end;
            v222.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1179 ]]
                return "rbxassetid://9181110093";
            end;
            v222.apply_to_emitter = function(p223, p224) --[[ Name: apply_to_emitter ]] --[[ Line: 1180 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p224)
                f_apply_simple_size_anim(p224)
                f_apply_simple_transparency_anim(p224)
                p224.Rate = 20
                p224.Texture = p223:get_image()
            end;
            return v222;
        end)()))
        v_u_17:add_fevericon_for_id(77, ((function() --[[ Line: 1189 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v225 = v_u_5.FeverIconInfoBase:new()
            v225.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1191 ]]
                return "Smug";
            end;
            v225.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1192 ]]
                return "rbxassetid://15100046775";
            end;
            v225.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1193 ]]
                return "rbxassetid://15100046836";
            end;
            v225.apply_to_emitter = function(p226, p227) --[[ Name: apply_to_emitter ]] --[[ Line: 1194 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p227)
                f_apply_simple_size_anim(p227)
                f_apply_simple_transparency_anim(p227)
                p227.Rate = 20
                p227.Texture = p226:get_image()
            end;
            return v225;
        end)()))
        v_u_17:add_fevericon_for_id(78, ((function() --[[ Line: 1203 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v228 = v_u_5.FeverIconInfoBase:new()
            v228.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1205 ]]
                return "Stonks";
            end;
            v228.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1206 ]]
                return "rbxassetid://9187823107";
            end;
            v228.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1207 ]]
                return "rbxassetid://9187823229";
            end;
            v228.apply_to_emitter = function(p229, p230) --[[ Name: apply_to_emitter ]] --[[ Line: 1208 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p230)
                f_apply_simple_size_anim(p230)
                f_apply_simple_transparency_anim(p230)
                p230.Rate = 20
                p230.Texture = p229:get_image()
            end;
            return v228;
        end)()))
        v_u_17:add_fevericon_for_id(79, ((function() --[[ Line: 1217 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v231 = v_u_5.FeverIconInfoBase:new()
            v231.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1219 ]]
                return "Let\'s GOOOOOOOOOOO";
            end;
            v231.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1220 ]]
                return "rbxassetid://15100046719";
            end;
            v231.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1221 ]]
                return "rbxassetid://15100046632";
            end;
            v231.apply_to_emitter = function(p232, p233) --[[ Name: apply_to_emitter ]] --[[ Line: 1222 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p233)
                f_apply_simple_size_anim(p233)
                f_apply_simple_transparency_anim(p233)
                p233.Rate = 20
                p233.Texture = p232:get_image()
            end;
            return v231;
        end)()))
        v_u_17:add_fevericon_for_id(80, ((function() --[[ Line: 1231 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v234 = v_u_5.FeverIconInfoBase:new()
            v234.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1233 ]]
                return "Meme Man";
            end;
            v234.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1234 ]]
                return "rbxassetid://9187823508";
            end;
            v234.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1235 ]]
                return "rbxassetid://9187823624";
            end;
            v234.apply_to_emitter = function(p235, p236) --[[ Name: apply_to_emitter ]] --[[ Line: 1236 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p236)
                f_apply_simple_size_anim(p236)
                f_apply_simple_transparency_anim(p236)
                p236.Rate = 20
                p236.Texture = p235:get_image()
            end;
            return v234;
        end)()))
        v_u_17:add_fevericon_for_id(81, ((function() --[[ Line: 1245 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v237 = v_u_5.FeverIconInfoBase:new()
            v237.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1247 ]]
                return "Just Right";
            end;
            v237.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1248 ]]
                return "rbxassetid://9187823725";
            end;
            v237.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1249 ]]
                return "rbxassetid://9187823813";
            end;
            v237.apply_to_emitter = function(p238, p239) --[[ Name: apply_to_emitter ]] --[[ Line: 1250 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p239)
                f_apply_simple_size_anim(p239)
                f_apply_simple_transparency_anim(p239)
                p239.Rate = 20
                p239.Texture = p238:get_image()
            end;
            return v237;
        end)()))
        v_u_17:add_fevericon_for_id(82, ((function() --[[ Line: 1259 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v240 = v_u_5.FeverIconInfoBase:new()
            v240.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1261 ]]
                return "Grafix Cat";
            end;
            v240.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1262 ]]
                return "rbxassetid://9187823897";
            end;
            v240.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1263 ]]
                return "rbxassetid://9187824056";
            end;
            v240.apply_to_emitter = function(p241, p242) --[[ Name: apply_to_emitter ]] --[[ Line: 1264 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p242)
                f_apply_simple_size_anim(p242)
                f_apply_simple_transparency_anim(p242)
                p242.Rate = 20
                p242.Texture = p241:get_image()
            end;
            return v240;
        end)()))
        v_u_17:add_fevericon_for_id(83, ((function() --[[ Line: 1273 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v243 = v_u_5.FeverIconInfoBase:new()
            v243.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1275 ]]
                return "Deal With It (Starlet)";
            end;
            v243.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1276 ]]
                return "rbxassetid://9187824203";
            end;
            v243.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1277 ]]
                return "rbxassetid://9187824316";
            end;
            v243.apply_to_emitter = function(p244, p245) --[[ Name: apply_to_emitter ]] --[[ Line: 1278 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p245)
                f_apply_simple_size_anim(p245)
                f_apply_simple_transparency_anim(p245)
                p245.Rate = 20
                p245.Texture = p244:get_image()
            end;
            return v243;
        end)()))
        v_u_17:add_fevericon_for_id(84, ((function() --[[ Line: 1287 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v246 = v_u_5.FeverIconInfoBase:new()
            v246.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1289 ]]
                return "Asteroid\'s Dream (brz1128)";
            end;
            v246.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1290 ]]
                return "rbxassetid://9307113678";
            end;
            v246.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1291 ]]
                return "rbxassetid://9307113883";
            end;
            v246.apply_to_emitter = function(p247, p248) --[[ Name: apply_to_emitter ]] --[[ Line: 1292 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p248)
                f_apply_simple_size_anim(p248)
                f_apply_simple_transparency_anim(p248)
                p248.Rate = 20
                p248.Texture = p247:get_image()
            end;
            return v246;
        end)()))
        v_u_17:add_fevericon_for_id(85, ((function() --[[ Line: 1301 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v249 = v_u_5.FeverIconInfoBase:new()
            v249.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1303 ]]
                return "Kurokotei";
            end;
            v249.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1304 ]]
                return "rbxassetid://9371413231";
            end;
            v249.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1305 ]]
                return "rbxassetid://9371413433";
            end;
            v249.apply_to_emitter = function(p250, p251) --[[ Name: apply_to_emitter ]] --[[ Line: 1306 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p251)
                f_apply_simple_size_anim(p251)
                f_apply_simple_transparency_anim(p251)
                p251.Rate = 20
                p251.Texture = p250:get_image()
            end;
            return v249;
        end)()))
        v_u_17:add_fevericon_for_id(86, ((function() --[[ Line: 1315 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v252 = v_u_5.FeverIconInfoBase:new()
            v252.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1317 ]]
                return "Angry Kurokotei Noises";
            end;
            v252.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1318 ]]
                return "rbxassetid://9380614511";
            end;
            v252.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1319 ]]
                return "rbxassetid://9380614834";
            end;
            v252.apply_to_emitter = function(p253, p254) --[[ Name: apply_to_emitter ]] --[[ Line: 1320 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p254)
                f_apply_simple_size_anim(p254)
                f_apply_simple_transparency_anim(p254)
                p254.Rate = 20
                p254.Texture = p253:get_image()
            end;
            return v252;
        end)()))
        v_u_17:add_fevericon_for_id(87, ((function() --[[ Line: 1329 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v255 = v_u_5.FeverIconInfoBase:new()
            v255.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1331 ]]
                return "Viyella";
            end;
            v255.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1332 ]]
                return "rbxassetid://9432000914";
            end;
            v255.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1333 ]]
                return "rbxassetid://9432001124";
            end;
            v255.apply_to_emitter = function(p256, p257) --[[ Name: apply_to_emitter ]] --[[ Line: 1334 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p257)
                f_apply_simple_size_anim(p257)
                f_apply_simple_transparency_anim(p257)
                p257.Rate = 20
                p257.Texture = p256:get_image()
            end;
            return v255;
        end)()))
        v_u_17:add_fevericon_for_id(88, ((function() --[[ Line: 1343 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v258 = v_u_5.FeverIconInfoBase:new()
            v258.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1345 ]]
                return "Ponchi Pop";
            end;
            v258.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1346 ]]
                return "rbxassetid://9562107358";
            end;
            v258.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1347 ]]
                return "rbxassetid://9562107540";
            end;
            v258.apply_to_emitter = function(p259, p260) --[[ Name: apply_to_emitter ]] --[[ Line: 1348 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p260)
                f_apply_simple_size_anim(p260)
                f_apply_simple_transparency_anim(p260)
                p260.Rate = 20
                p260.Texture = p259:get_image()
            end;
            return v258;
        end)()))
        v_u_17:add_fevericon_for_id(89, ((function() --[[ Line: 1357 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v261 = v_u_5.FeverIconInfoBase:new()
            v261.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1359 ]]
                return "t0y0u";
            end;
            v261.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1360 ]]
                return "rbxassetid://9599825233";
            end;
            v261.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1361 ]]
                return "rbxassetid://9599825342";
            end;
            v261.apply_to_emitter = function(p262, p263) --[[ Name: apply_to_emitter ]] --[[ Line: 1362 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p263)
                f_apply_simple_size_anim(p263)
                f_apply_simple_transparency_anim(p263)
                p263.Rate = 20
                p263.Texture = p262:get_image()
            end;
            return v261;
        end)()))
        v_u_17:add_fevericon_for_id(90, ((function() --[[ Line: 1371 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v264 = v_u_5.FeverIconInfoBase:new()
            v264.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1373 ]]
                return "garlagal";
            end;
            v264.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1374 ]]
                return "rbxassetid://9621609099";
            end;
            v264.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1375 ]]
                return "rbxassetid://9621609326";
            end;
            v264.apply_to_emitter = function(p265, p266) --[[ Name: apply_to_emitter ]] --[[ Line: 1376 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p266)
                f_apply_simple_size_anim(p266)
                f_apply_simple_transparency_anim(p266)
                p266.Rate = 20
                p266.Texture = p265:get_image()
            end;
            return v264;
        end)()))
        v_u_17:add_fevericon_for_id(91, ((function() --[[ Line: 1385 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v267 = v_u_5.FeverIconInfoBase:new()
            v267.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1387 ]]
                return "UNDEAD CORPORATION";
            end;
            v267.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1388 ]]
                return "rbxassetid://9673170056";
            end;
            v267.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1389 ]]
                return "rbxassetid://9673170317";
            end;
            v267.apply_to_emitter = function(p268, p269) --[[ Name: apply_to_emitter ]] --[[ Line: 1390 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p269)
                f_apply_simple_size_anim(p269)
                f_apply_simple_transparency_anim(p269)
                p269.Rate = 20
                p269.Texture = p268:get_image()
            end;
            return v267;
        end)()))
        v_u_17:add_fevericon_for_id(92, ((function() --[[ Line: 1399 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v270 = v_u_5.FeverIconInfoBase:new()
            v270.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1401 ]]
                return "RiraN";
            end;
            v270.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1402 ]]
                return "rbxassetid://9712478738";
            end;
            v270.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1403 ]]
                return "rbxassetid://9712478845";
            end;
            v270.apply_to_emitter = function(p271, p272) --[[ Name: apply_to_emitter ]] --[[ Line: 1404 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p272)
                f_apply_simple_size_anim(p272)
                f_apply_simple_transparency_anim(p272)
                p272.Rate = 20
                p272.Texture = p271:get_image()
            end;
            return v270;
        end)()))
        v_u_17:add_fevericon_for_id(93, ((function() --[[ Line: 1413 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v273 = v_u_5.FeverIconInfoBase:new()
            v273.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1415 ]]
                return "UNIVERSE (brz1128)";
            end;
            v273.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1416 ]]
                return "rbxassetid://9802790222";
            end;
            v273.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1417 ]]
                return "rbxassetid://9802790380";
            end;
            v273.apply_to_emitter = function(p274, p275) --[[ Name: apply_to_emitter ]] --[[ Line: 1418 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p275)
                f_apply_simple_size_anim(p275)
                f_apply_simple_transparency_anim(p275)
                p275.Rate = 20
                p275.Texture = p274:get_image()
            end;
            return v273;
        end)()))
        v_u_17:add_fevericon_for_id(94, ((function() --[[ Line: 1427 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v276 = v_u_5.FeverIconInfoBase:new()
            v276.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1429 ]]
                return "Shaii (Geoxor)";
            end;
            v276.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1430 ]]
                return "rbxassetid://9850868169";
            end;
            v276.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1431 ]]
                return "rbxassetid://9850868387";
            end;
            v276.apply_to_emitter = function(p277, p278) --[[ Name: apply_to_emitter ]] --[[ Line: 1432 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p278)
                f_apply_simple_size_anim(p278)
                f_apply_simple_transparency_anim(p278)
                p278.Rate = 20
                p278.Texture = p277:get_image()
            end;
            return v276;
        end)()))
        v_u_17:add_fevericon_for_id(95, ((function() --[[ Line: 1441 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v279 = v_u_5.FeverIconInfoBase:new()
            v279.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1443 ]]
                return "Kurante (Freedom Dive)";
            end;
            v279.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1444 ]]
                return "rbxassetid://9914716537";
            end;
            v279.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1445 ]]
                return "rbxassetid://9914716743";
            end;
            v279.apply_to_emitter = function(p280, p281) --[[ Name: apply_to_emitter ]] --[[ Line: 1446 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p281)
                f_apply_simple_size_anim(p281)
                f_apply_simple_transparency_anim(p281)
                p281.Rate = 20
                p281.Texture = p280:get_image()
            end;
            return v279;
        end)()))
        v_u_17:add_fevericon_for_id(96, ((function() --[[ Line: 1455 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v282 = v_u_5.FeverIconInfoBase:new()
            v282.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1457 ]]
                return "World Fragments (xi)";
            end;
            v282.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1458 ]]
                return "rbxassetid://9914716434";
            end;
            v282.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1459 ]]
                return "rbxassetid://9914716632";
            end;
            v282.apply_to_emitter = function(p283, p284) --[[ Name: apply_to_emitter ]] --[[ Line: 1460 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p284)
                f_apply_simple_size_anim(p284)
                f_apply_simple_transparency_anim(p284)
                p284.Rate = 20
                p284.Texture = p283:get_image()
            end;
            return v282;
        end)()))
        v_u_17:add_fevericon_for_id(97, ((function() --[[ Line: 1469 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v285 = v_u_5.FeverIconInfoBase:new()
            v285.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1471 ]]
                return "Maliboux";
            end;
            v285.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1472 ]]
                return "rbxassetid://9985788144";
            end;
            v285.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1473 ]]
                return "rbxassetid://9985788282";
            end;
            v285.apply_to_emitter = function(p286, p287) --[[ Name: apply_to_emitter ]] --[[ Line: 1474 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p287)
                f_apply_simple_size_anim(p287)
                f_apply_simple_transparency_anim(p287)
                p287.Rate = 20
                p287.Texture = p286:get_image()
            end;
            return v285;
        end)()))
        v_u_17:add_fevericon_for_id(98, ((function() --[[ Line: 1483 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v288 = v_u_5.FeverIconInfoBase:new()
            v288.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1485 ]]
                return "Ringmaster Roxie";
            end;
            v288.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1486 ]]
                return "rbxassetid://10078812585";
            end;
            v288.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1487 ]]
                return "rbxassetid://10078813032";
            end;
            v288.apply_to_emitter = function(p289, p290) --[[ Name: apply_to_emitter ]] --[[ Line: 1488 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p290)
                f_apply_simple_size_anim(p290)
                f_apply_simple_transparency_anim(p290)
                p290.Rate = 20
                p290.Texture = p289:get_image()
            end;
            return v288;
        end)()))
        v_u_17:add_fevericon_for_id(99, ((function() --[[ Line: 1497 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v291 = v_u_5.FeverIconInfoBase:new()
            v291.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1499 ]]
                return "NOMA";
            end;
            v291.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1500 ]]
                return "rbxassetid://10078812902";
            end;
            v291.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1501 ]]
                return "rbxassetid://10078813121";
            end;
            v291.apply_to_emitter = function(p292, p293) --[[ Name: apply_to_emitter ]] --[[ Line: 1502 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p293)
                f_apply_simple_size_anim(p293)
                f_apply_simple_transparency_anim(p293)
                p293.Rate = 20
                p293.Texture = p292:get_image()
            end;
            return v291;
        end)()))
        v_u_17:add_fevericon_for_id(100, ((function() --[[ Line: 1511 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v294 = v_u_5.FeverIconInfoBase:new()
            v294.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1513 ]]
                return "Monstercat Supporter";
            end;
            v294.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1514 ]]
                return "rbxassetid://10151876739";
            end;
            v294.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1515 ]]
                return "rbxassetid://10151876877";
            end;
            v294.apply_to_emitter = function(p295, p296) --[[ Name: apply_to_emitter ]] --[[ Line: 1516 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p296)
                f_apply_simple_size_anim(p296)
                f_apply_simple_transparency_anim(p296)
                p296.Rate = 20
                p296.Texture = p295:get_image()
            end;
            return v294;
        end)()))
        v_u_17:add_fevericon_for_id(101, ((function() --[[ Line: 1525 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v297 = v_u_5.FeverIconInfoBase:new()
            v297.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1527 ]]
                return "Wednesday Frog";
            end;
            v297.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1528 ]]
                return "rbxassetid://10165093154";
            end;
            v297.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1529 ]]
                return "rbxassetid://10163644155";
            end;
            v297.apply_to_emitter = function(p298, p299) --[[ Name: apply_to_emitter ]] --[[ Line: 1530 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p299)
                f_apply_simple_size_anim(p299)
                f_apply_simple_transparency_anim(p299)
                p299.Rate = 20
                p299.Texture = p298:get_image()
            end;
            return v297;
        end)()))
        v_u_17:add_fevericon_for_id(102, ((function() --[[ Line: 1539 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v300 = v_u_5.FeverIconInfoBase:new()
            v300.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1541 ]]
                return "Polite Cat";
            end;
            v300.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1542 ]]
                return "rbxassetid://10163644286";
            end;
            v300.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1543 ]]
                return "rbxassetid://10163644516";
            end;
            v300.apply_to_emitter = function(p301, p302) --[[ Name: apply_to_emitter ]] --[[ Line: 1544 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p302)
                f_apply_simple_size_anim(p302)
                f_apply_simple_transparency_anim(p302)
                p302.Rate = 20
                p302.Texture = p301:get_image()
            end;
            return v300;
        end)()))
        v_u_17:add_fevericon_for_id(103, ((function() --[[ Line: 1553 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v303 = v_u_5.FeverIconInfoBase:new()
            v303.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1555 ]]
                return "Happyjack";
            end;
            v303.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1556 ]]
                return "rbxassetid://10163645052";
            end;
            v303.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1557 ]]
                return "rbxassetid://10163645221";
            end;
            v303.apply_to_emitter = function(p304, p305) --[[ Name: apply_to_emitter ]] --[[ Line: 1558 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p305)
                f_apply_simple_size_anim(p305)
                f_apply_simple_transparency_anim(p305)
                p305.Rate = 20
                p305.Texture = p304:get_image()
            end;
            return v303;
        end)()))
        v_u_17:add_fevericon_for_id(104, ((function() --[[ Line: 1567 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v306 = v_u_5.FeverIconInfoBase:new()
            v306.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1569 ]]
                return "Glowing Brain";
            end;
            v306.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1570 ]]
                return "rbxassetid://10163645446";
            end;
            v306.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1571 ]]
                return "rbxassetid://10163645556";
            end;
            v306.apply_to_emitter = function(p307, p308) --[[ Name: apply_to_emitter ]] --[[ Line: 1572 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p308)
                f_apply_simple_size_anim(p308)
                f_apply_simple_transparency_anim(p308)
                p308.Rate = 20
                p308.Texture = p307:get_image()
            end;
            return v306;
        end)()))
        v_u_17:add_fevericon_for_id(105, ((function() --[[ Line: 1581 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v309 = v_u_5.FeverIconInfoBase:new()
            v309.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1583 ]]
                return "Illuminati";
            end;
            v309.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1584 ]]
                return "rbxassetid://10163645799";
            end;
            v309.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1585 ]]
                return "rbxassetid://10163645908";
            end;
            v309.apply_to_emitter = function(p310, p311) --[[ Name: apply_to_emitter ]] --[[ Line: 1586 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p311)
                f_apply_simple_size_anim(p311)
                f_apply_simple_transparency_anim(p311)
                p311.Rate = 20
                p311.Texture = p310:get_image()
            end;
            return v309;
        end)()))
        v_u_17:add_fevericon_for_id(106, ((function() --[[ Line: 1595 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v312 = v_u_5.FeverIconInfoBase:new()
            v312.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1597 ]]
                return "Eggdog";
            end;
            v312.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1598 ]]
                return "rbxassetid://10163646054";
            end;
            v312.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1599 ]]
                return "rbxassetid://10163646190";
            end;
            v312.apply_to_emitter = function(p313, p314) --[[ Name: apply_to_emitter ]] --[[ Line: 1600 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p314)
                f_apply_simple_size_anim(p314)
                f_apply_simple_transparency_anim(p314)
                p314.Rate = 20
                p314.Texture = p313:get_image()
            end;
            return v312;
        end)()))
        v_u_17:add_fevericon_for_id(107, ((function() --[[ Line: 1609 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v315 = v_u_5.FeverIconInfoBase:new()
            v315.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1611 ]]
                return "Disgusted";
            end;
            v315.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1612 ]]
                return "rbxassetid://10163646297";
            end;
            v315.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1613 ]]
                return "rbxassetid://10163646460";
            end;
            v315.apply_to_emitter = function(p316, p317) --[[ Name: apply_to_emitter ]] --[[ Line: 1614 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p317)
                f_apply_simple_size_anim(p317)
                f_apply_simple_transparency_anim(p317)
                p317.Rate = 20
                p317.Texture = p316:get_image()
            end;
            return v315;
        end)()))
        v_u_17:add_fevericon_for_id(108, ((function() --[[ Line: 1623 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v318 = v_u_5.FeverIconInfoBase:new()
            v318.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1625 ]]
                return "Cheems";
            end;
            v318.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1626 ]]
                return "rbxassetid://10163646698";
            end;
            v318.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1627 ]]
                return "rbxassetid://10163646874";
            end;
            v318.apply_to_emitter = function(p319, p320) --[[ Name: apply_to_emitter ]] --[[ Line: 1628 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p320)
                f_apply_simple_size_anim(p320)
                f_apply_simple_transparency_anim(p320)
                p320.Rate = 20
                p320.Texture = p319:get_image()
            end;
            return v318;
        end)()))
        v_u_17:add_fevericon_for_id(109, ((function() --[[ Line: 1637 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v321 = v_u_5.FeverIconInfoBase:new()
            v321.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1639 ]]
                return "Angery";
            end;
            v321.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1640 ]]
                return "rbxassetid://10163646991";
            end;
            v321.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1641 ]]
                return "rbxassetid://10163647203";
            end;
            v321.apply_to_emitter = function(p322, p323) --[[ Name: apply_to_emitter ]] --[[ Line: 1642 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p323)
                f_apply_simple_size_anim(p323)
                f_apply_simple_transparency_anim(p323)
                p323.Rate = 20
                p323.Texture = p322:get_image()
            end;
            return v321;
        end)()))
        v_u_17:add_fevericon_for_id(110, ((function() --[[ Line: 1651 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v324 = v_u_5.FeverIconInfoBase:new()
            v324.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1653 ]]
                return "Poo";
            end;
            v324.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1654 ]]
                return "rbxassetid://10163647746";
            end;
            v324.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1655 ]]
                return "rbxassetid://10163647894";
            end;
            v324.apply_to_emitter = function(p325, p326) --[[ Name: apply_to_emitter ]] --[[ Line: 1656 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p326)
                f_apply_simple_size_anim(p326)
                f_apply_simple_transparency_anim(p326)
                p326.Rate = 20
                p326.Texture = p325:get_image()
            end;
            return v324;
        end)()))
        v_u_17:add_fevericon_for_id(111, ((function() --[[ Line: 1665 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v327 = v_u_5.FeverIconInfoBase:new()
            v327.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1667 ]]
                return "Soccer Mommy Cap";
            end;
            v327.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1668 ]]
                return "rbxassetid://10207465474";
            end;
            v327.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1669 ]]
                return "rbxassetid://10207465587";
            end;
            v327.apply_to_emitter = function(p328, p329) --[[ Name: apply_to_emitter ]] --[[ Line: 1670 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p329)
                f_apply_simple_size_anim(p329)
                f_apply_simple_transparency_anim(p329)
                p329.Rate = 20
                p329.Texture = p328:get_image()
            end;
            return v327;
        end)()))
        v_u_17:add_fevericon_for_id(112, ((function() --[[ Line: 1679 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v330 = v_u_5.FeverIconInfoBase:new()
            v330.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1681 ]]
                return "FNF Girlfriend";
            end;
            v330.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1682 ]]
                return "rbxassetid://14811738825";
            end;
            v330.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1683 ]]
                return "rbxassetid://14811738936";
            end;
            v330.apply_to_emitter = function(p331, p332) --[[ Name: apply_to_emitter ]] --[[ Line: 1684 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p332)
                f_apply_simple_size_anim(p332)
                f_apply_simple_transparency_anim(p332)
                p332.Rate = 20
                p332.Texture = p331:get_image()
            end;
            return v330;
        end)()))
        v_u_17:add_fevericon_for_id(113, ((function() --[[ Line: 1693 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v333 = v_u_5.FeverIconInfoBase:new()
            v333.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1695 ]]
                return "Gold Rush Kid";
            end;
            v333.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1696 ]]
                return "rbxassetid://10356396771";
            end;
            v333.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1697 ]]
                return "rbxassetid://10356397126";
            end;
            v333.apply_to_emitter = function(p334, p335) --[[ Name: apply_to_emitter ]] --[[ Line: 1698 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p335)
                f_apply_simple_size_anim(p335)
                f_apply_simple_transparency_anim(p335)
                p335.Rate = 20
                p335.Texture = p334:get_image()
            end;
            return v333;
        end)()))
        v_u_17:add_fevericon_for_id(114, ((function() --[[ Line: 1707 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v336 = v_u_5.FeverIconInfoBase:new()
            v336.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1709 ]]
                return "Team Grimoire";
            end;
            v336.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1710 ]]
                return "rbxassetid://10358939002";
            end;
            v336.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1711 ]]
                return "rbxassetid://10358939485";
            end;
            v336.apply_to_emitter = function(p337, p338) --[[ Name: apply_to_emitter ]] --[[ Line: 1712 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p338)
                f_apply_simple_size_anim(p338)
                f_apply_simple_transparency_anim(p338)
                p338.Rate = 20
                p338.Texture = p337:get_image()
            end;
            return v336;
        end)()))
        v_u_17:add_fevericon_for_id(115, ((function() --[[ Line: 1721 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v339 = v_u_5.FeverIconInfoBase:new()
            v339.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1723 ]]
                return "Restriction";
            end;
            v339.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1724 ]]
                return "rbxassetid://10358939288";
            end;
            v339.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1725 ]]
                return "rbxassetid://10358939801";
            end;
            v339.apply_to_emitter = function(p340, p341) --[[ Name: apply_to_emitter ]] --[[ Line: 1726 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p341)
                f_apply_simple_size_anim(p341)
                f_apply_simple_transparency_anim(p341)
                p341.Rate = 20
                p341.Texture = p340:get_image()
            end;
            return v339;
        end)()))
        v_u_17:add_fevericon_for_id(116, ((function() --[[ Line: 1735 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v342 = v_u_5.FeverIconInfoBase:new()
            v342.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1737 ]]
                return "Determination (Laur)";
            end;
            v342.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1738 ]]
                return "rbxassetid://10562478439";
            end;
            v342.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1739 ]]
                return "rbxassetid://10562478682";
            end;
            v342.apply_to_emitter = function(p343, p344) --[[ Name: apply_to_emitter ]] --[[ Line: 1740 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p344)
                f_apply_simple_size_anim(p344)
                f_apply_simple_transparency_anim(p344)
                p344.Rate = 20
                p344.Texture = p343:get_image()
            end;
            return v342;
        end)()))
        v_u_17:add_fevericon_for_id(117, ((function() --[[ Line: 1749 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v345 = v_u_5.FeverIconInfoBase:new()
            v345.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1751 ]]
                return "Ark Six (Se-U-Ra)";
            end;
            v345.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1752 ]]
                return "rbxassetid://10642426368";
            end;
            v345.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1753 ]]
                return "rbxassetid://10642426252";
            end;
            v345.apply_to_emitter = function(p346, p347) --[[ Name: apply_to_emitter ]] --[[ Line: 1754 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p347)
                f_apply_simple_size_anim(p347)
                f_apply_simple_transparency_anim(p347)
                p347.Rate = 20
                p347.Texture = p346:get_image()
            end;
            return v345;
        end)()))
        v_u_17:add_fevericon_for_id(118, ((function() --[[ Line: 1763 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v348 = v_u_5.FeverIconInfoBase:new()
            v348.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1765 ]]
                return "Rutra";
            end;
            v348.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1766 ]]
                return "rbxassetid://10843378091";
            end;
            v348.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1767 ]]
                return "rbxassetid://10395959471";
            end;
            v348.apply_to_emitter = function(p349, p350) --[[ Name: apply_to_emitter ]] --[[ Line: 1768 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p350)
                f_apply_simple_size_anim(p350)
                f_apply_simple_transparency_anim(p350)
                p350.Rate = 20
                p350.Texture = p349:get_image()
            end;
            return v348;
        end)()))
        v_u_17:add_fevericon_for_id(119, ((function() --[[ Line: 1777 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v351 = v_u_5.FeverIconInfoBase:new()
            v351.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1779 ]]
                return "Fire! (Rutra)";
            end;
            v351.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1780 ]]
                return "rbxassetid://10843378041";
            end;
            v351.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1781 ]]
                return "rbxassetid://10843378141";
            end;
            v351.apply_to_emitter = function(p352, p353) --[[ Name: apply_to_emitter ]] --[[ Line: 1782 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p353)
                f_apply_simple_size_anim(p353)
                f_apply_simple_transparency_anim(p353)
                p353.Rate = 20
                p353.Texture = p352:get_image()
            end;
            return v351;
        end)()))
        v_u_17:add_fevericon_for_id(120, ((function() --[[ Line: 1791 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v354 = v_u_5.FeverIconInfoBase:new()
            v354.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1793 ]]
                return "Bloxy Trophy";
            end;
            v354.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1794 ]]
                return "rbxassetid://10892032426";
            end;
            v354.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1795 ]]
                return "rbxassetid://10892032565";
            end;
            v354.apply_to_emitter = function(p355, p356) --[[ Name: apply_to_emitter ]] --[[ Line: 1796 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p356)
                f_apply_simple_size_anim(p356)
                f_apply_simple_transparency_anim(p356)
                p356.Rate = 20
                p356.Texture = p355:get_image()
            end;
            return v354;
        end)()))
        v_u_17:add_fevericon_for_id(121, ((function() --[[ Line: 1805 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v357 = v_u_5.FeverIconInfoBase:new()
            v357.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1807 ]]
                return "Reku Mochizuki";
            end;
            v357.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1808 ]]
                return "rbxassetid://10969991896";
            end;
            v357.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1809 ]]
                return "rbxassetid://10969991958";
            end;
            v357.apply_to_emitter = function(p358, p359) --[[ Name: apply_to_emitter ]] --[[ Line: 1810 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p359)
                f_apply_simple_size_anim(p359)
                f_apply_simple_transparency_anim(p359)
                p359.Rate = 20
                p359.Texture = p358:get_image()
            end;
            return v357;
        end)()))
        v_u_17:add_fevericon_for_id(122, ((function() --[[ Line: 1819 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v360 = v_u_5.FeverIconInfoBase:new()
            v360.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1821 ]]
                return "Ushi-chan (naruto2413)";
            end;
            v360.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1822 ]]
                return "rbxassetid://11110840067";
            end;
            v360.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1823 ]]
                return "rbxassetid://11110840200";
            end;
            v360.apply_to_emitter = function(p361, p362) --[[ Name: apply_to_emitter ]] --[[ Line: 1824 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p362)
                f_apply_simple_size_anim(p362)
                f_apply_simple_transparency_anim(p362)
                p362.Rate = 20
                p362.Texture = p361:get_image()
            end;
            return v360;
        end)()))
        v_u_17:add_fevericon_for_id(123, ((function() --[[ Line: 1833 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v363 = v_u_5.FeverIconInfoBase:new()
            v363.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1835 ]]
                return "Ardolf";
            end;
            v363.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1836 ]]
                return "rbxassetid://11184766819";
            end;
            v363.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1837 ]]
                return "rbxassetid://11184766923";
            end;
            v363.apply_to_emitter = function(p364, p365) --[[ Name: apply_to_emitter ]] --[[ Line: 1838 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p365)
                f_apply_simple_size_anim(p365)
                f_apply_simple_transparency_anim(p365)
                p365.Rate = 20
                p365.Texture = p364:get_image()
            end;
            return v363;
        end)()))
        v_u_17:add_fevericon_for_id(124, ((function() --[[ Line: 1847 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v366 = v_u_5.FeverIconInfoBase:new()
            v366.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1849 ]]
                return "Louder Now (Tobu)";
            end;
            v366.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1850 ]]
                return "rbxassetid://11266598702";
            end;
            v366.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1851 ]]
                return "rbxassetid://11266598954";
            end;
            v366.apply_to_emitter = function(p367, p368) --[[ Name: apply_to_emitter ]] --[[ Line: 1852 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p368)
                f_apply_simple_size_anim(p368)
                f_apply_simple_transparency_anim(p368)
                p368.Rate = 20
                p368.Texture = p367:get_image()
            end;
            return v366;
        end)()))
        v_u_17:add_fevericon_for_id(125, ((function() --[[ Line: 1861 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v369 = v_u_5.FeverIconInfoBase:new()
            v369.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1863 ]]
                return "seatrus";
            end;
            v369.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1864 ]]
                return "rbxassetid://11330168526";
            end;
            v369.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1865 ]]
                return "rbxassetid://11330168657";
            end;
            v369.apply_to_emitter = function(p370, p371) --[[ Name: apply_to_emitter ]] --[[ Line: 1866 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p371)
                f_apply_simple_size_anim(p371)
                f_apply_simple_transparency_anim(p371)
                p371.Rate = 20
                p371.Texture = p370:get_image()
            end;
            return v369;
        end)()))
        v_u_17:add_fevericon_for_id(126, ((function() --[[ Line: 1875 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v372 = v_u_5.FeverIconInfoBase:new()
            v372.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1877 ]]
                return "Halloween Witch Teresa";
            end;
            v372.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1878 ]]
                return "rbxassetid://11389240355";
            end;
            v372.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1879 ]]
                return "rbxassetid://11389240417";
            end;
            v372.apply_to_emitter = function(p373, p374) --[[ Name: apply_to_emitter ]] --[[ Line: 1880 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p374)
                f_apply_simple_size_anim(p374)
                f_apply_simple_transparency_anim(p374)
                p374.Rate = 20
                p374.Texture = p373:get_image()
            end;
            return v372;
        end)()))
        v_u_17:add_fevericon_for_id(127, ((function() --[[ Line: 1889 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v375 = v_u_5.FeverIconInfoBase:new()
            v375.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1891 ]]
                return "Meant to Be (Slynk)";
            end;
            v375.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1892 ]]
                return "rbxassetid://11454557873";
            end;
            v375.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1893 ]]
                return "rbxassetid://11454503926";
            end;
            v375.apply_to_emitter = function(p376, p377) --[[ Name: apply_to_emitter ]] --[[ Line: 1894 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p377)
                f_apply_simple_size_anim(p377)
                f_apply_simple_transparency_anim(p377)
                p377.Rate = 20
                p377.Texture = p376:get_image()
            end;
            return v375;
        end)()))
        v_u_17:add_fevericon_for_id(128, ((function() --[[ Line: 1903 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v378 = v_u_5.FeverIconInfoBase:new()
            v378.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1905 ]]
                return "tv room";
            end;
            v378.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1906 ]]
                return "rbxassetid://11509560603";
            end;
            v378.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1907 ]]
                return "rbxassetid://10395959601";
            end;
            v378.apply_to_emitter = function(p379, p380) --[[ Name: apply_to_emitter ]] --[[ Line: 1908 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p380)
                f_apply_simple_size_anim(p380)
                f_apply_simple_transparency_anim(p380)
                p380.Rate = 20
                p380.Texture = p379:get_image()
            end;
            return v378;
        end)()))
        v_u_17:add_fevericon_for_id(129, ((function() --[[ Line: 1917 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v381 = v_u_5.FeverIconInfoBase:new()
            v381.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1919 ]]
                return "Summertime Marie";
            end;
            v381.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1920 ]]
                return "rbxassetid://11590540959";
            end;
            v381.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1921 ]]
                return "rbxassetid://11590541086";
            end;
            v381.apply_to_emitter = function(p382, p383) --[[ Name: apply_to_emitter ]] --[[ Line: 1922 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p383)
                f_apply_simple_size_anim(p383)
                f_apply_simple_transparency_anim(p383)
                p383.Rate = 20
                p383.Texture = p382:get_image()
            end;
            return v381;
        end)()))
        v_u_17:add_fevericon_for_id(130, ((function() --[[ Line: 1931 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v384 = v_u_5.FeverIconInfoBase:new()
            v384.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1933 ]]
                return "Kobaryo";
            end;
            v384.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1934 ]]
                return "rbxassetid://11638645520";
            end;
            v384.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1935 ]]
                return "rbxassetid://11638645841";
            end;
            v384.apply_to_emitter = function(p385, p386) --[[ Name: apply_to_emitter ]] --[[ Line: 1936 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p386)
                f_apply_simple_size_anim(p386)
                f_apply_simple_transparency_anim(p386)
                p386.Rate = 20
                p386.Texture = p385:get_image()
            end;
            return v384;
        end)()))
        v_u_17:add_fevericon_for_id(131, ((function() --[[ Line: 1945 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v387 = v_u_5.FeverIconInfoBase:new()
            v387.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1947 ]]
                return "Cake (Make a Cake)";
            end;
            v387.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1948 ]]
                return "rbxassetid://11830971993";
            end;
            v387.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1949 ]]
                return "rbxassetid://11830972082";
            end;
            v387.apply_to_emitter = function(p388, p389) --[[ Name: apply_to_emitter ]] --[[ Line: 1950 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p389)
                f_apply_simple_size_anim(p389)
                f_apply_simple_transparency_anim(p389)
                p389.Rate = 20
                p389.Texture = p388:get_image()
            end;
            return v387;
        end)()))
        v_u_17:add_fevericon_for_id(132, ((function() --[[ Line: 1959 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v390 = v_u_5.FeverIconInfoBase:new()
            v390.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1961 ]]
                return "RoBeats: Winter Edition";
            end;
            v390.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1962 ]]
                return "rbxassetid://11867741297";
            end;
            v390.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1963 ]]
                return "rbxassetid://11867741428";
            end;
            v390.apply_to_emitter = function(p391, p392) --[[ Name: apply_to_emitter ]] --[[ Line: 1964 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p392)
                f_apply_simple_size_anim(p392)
                f_apply_simple_transparency_anim(p392)
                p392.Rate = 20
                p392.Texture = p391:get_image()
            end;
            return v390;
        end)()))
        v_u_17:add_fevericon_for_id(133, ((function() --[[ Line: 1973 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v393 = v_u_5.FeverIconInfoBase:new()
            v393.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1975 ]]
                return "Bunny Zara";
            end;
            v393.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1976 ]]
                return "rbxassetid://11945362950";
            end;
            v393.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1977 ]]
                return "rbxassetid://11945363275";
            end;
            v393.apply_to_emitter = function(p394, p395) --[[ Name: apply_to_emitter ]] --[[ Line: 1978 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p395)
                f_apply_simple_size_anim(p395)
                f_apply_simple_transparency_anim(p395)
                p395.Rate = 20
                p395.Texture = p394:get_image()
            end;
            return v393;
        end)()))
        v_u_17:add_fevericon_for_id(134, ((function() --[[ Line: 1987 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v396 = v_u_5.FeverIconInfoBase:new()
            v396.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 1989 ]]
                return "Sound Space Cat";
            end;
            v396.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 1990 ]]
                return "rbxassetid://12100500863";
            end;
            v396.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 1991 ]]
                return "rbxassetid://12100501047";
            end;
            v396.apply_to_emitter = function(p397, p398) --[[ Name: apply_to_emitter ]] --[[ Line: 1992 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p398)
                f_apply_simple_size_anim(p398)
                f_apply_simple_transparency_anim(p398)
                p398.Rate = 20
                p398.Texture = p397:get_image()
            end;
            return v396;
        end)()))
        v_u_17:add_fevericon_for_id(135, ((function() --[[ Line: 2001 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_apply_default_emitter_properties, (ref 3): f_apply_simple_size_anim, (ref 4): f_apply_simple_transparency_anim ]]
            local v399 = v_u_5.FeverIconInfoBase:new()
            v399.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 2003 ]]
                return "Sound Space Logo";
            end;
            v399.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 2004 ]]
                return "rbxassetid://12100590989";
            end;
            v399.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 2005 ]]
                return "rbxassetid://12100587886";
            end;
            v399.apply_to_emitter = function(p400, p401) --[[ Name: apply_to_emitter ]] --[[ Line: 2006 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p401)
                f_apply_simple_size_anim(p401)
                f_apply_simple_transparency_anim(p401)
                p401.Rate = 20
                p401.Texture = p400:get_image()
            end;
            return v399;
        end)()))
        local v_u_402 = "Swole"
        local v_u_403 = "rbxassetid://12135430863"
        local v_u_404 = "http://www.roblox.com/asset/?id=12143731862"
        v_u_17:add_fevericon_for_id(136, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_402, (copy 3): v_u_403, (copy 4): v_u_404, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v405 = v_u_5.FeverIconInfoBase:new()
            v405.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_402 ]]
                return v_u_402;
            end;
            v405.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_403 ]]
                return v_u_403;
            end;
            v405.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_404 ]]
                return v_u_404;
            end;
            v405.apply_to_emitter = function(p406, p407) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p407)
                f_apply_simple_size_anim(p407)
                f_apply_simple_transparency_anim(p407)
                p407.Rate = 20
                p407.Texture = p406:get_image()
            end;
            return v405;
        end)()))
        local v_u_408 = "BOIIIIII"
        local v_u_409 = "rbxassetid://12135430995"
        local v_u_410 = "rbxassetid://12135432278"
        v_u_17:add_fevericon_for_id(137, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_408, (copy 3): v_u_409, (copy 4): v_u_410, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v411 = v_u_5.FeverIconInfoBase:new()
            v411.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_408 ]]
                return v_u_408;
            end;
            v411.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_409 ]]
                return v_u_409;
            end;
            v411.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_410 ]]
                return v_u_410;
            end;
            v411.apply_to_emitter = function(p412, p413) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p413)
                f_apply_simple_size_anim(p413)
                f_apply_simple_transparency_anim(p413)
                p413.Rate = 20
                p413.Texture = p412:get_image()
            end;
            return v411;
        end)()))
        local v_u_414 = "Scared"
        local v_u_415 = "rbxassetid://12135431147"
        local v_u_416 = "rbxassetid://12135432455"
        v_u_17:add_fevericon_for_id(139, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_414, (copy 3): v_u_415, (copy 4): v_u_416, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v417 = v_u_5.FeverIconInfoBase:new()
            v417.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_414 ]]
                return v_u_414;
            end;
            v417.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_415 ]]
                return v_u_415;
            end;
            v417.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_416 ]]
                return v_u_416;
            end;
            v417.apply_to_emitter = function(p418, p419) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p419)
                f_apply_simple_size_anim(p419)
                f_apply_simple_transparency_anim(p419)
                p419.Rate = 20
                p419.Texture = p418:get_image()
            end;
            return v417;
        end)()))
        local v_u_420 = "Don\'t Press The Red Button!"
        local v_u_421 = "rbxassetid://12135431323"
        local v_u_422 = "rbxassetid://12135432668"
        v_u_17:add_fevericon_for_id(140, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_420, (copy 3): v_u_421, (copy 4): v_u_422, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v423 = v_u_5.FeverIconInfoBase:new()
            v423.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_420 ]]
                return v_u_420;
            end;
            v423.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_421 ]]
                return v_u_421;
            end;
            v423.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_422 ]]
                return v_u_422;
            end;
            v423.apply_to_emitter = function(p424, p425) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p425)
                f_apply_simple_size_anim(p425)
                f_apply_simple_transparency_anim(p425)
                p425.Rate = 20
                p425.Texture = p424:get_image()
            end;
            return v423;
        end)()))
        local v_u_426 = "Officer Penguin (No Anime)"
        local v_u_427 = "rbxassetid://12135431449"
        local v_u_428 = "rbxassetid://12135432805"
        v_u_17:add_fevericon_for_id(141, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_426, (copy 3): v_u_427, (copy 4): v_u_428, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v429 = v_u_5.FeverIconInfoBase:new()
            v429.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_426 ]]
                return v_u_426;
            end;
            v429.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_427 ]]
                return v_u_427;
            end;
            v429.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_428 ]]
                return v_u_428;
            end;
            v429.apply_to_emitter = function(p430, p431) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p431)
                f_apply_simple_size_anim(p431)
                f_apply_simple_transparency_anim(p431)
                p431.Rate = 20
                p431.Texture = p430:get_image()
            end;
            return v429;
        end)()))
        local v_u_432 = "nerdy"
        local v_u_433 = "rbxassetid://12135431676"
        local v_u_434 = "rbxassetid://12135432938"
        v_u_17:add_fevericon_for_id(142, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_432, (copy 3): v_u_433, (copy 4): v_u_434, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v435 = v_u_5.FeverIconInfoBase:new()
            v435.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_432 ]]
                return v_u_432;
            end;
            v435.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_433 ]]
                return v_u_433;
            end;
            v435.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_434 ]]
                return v_u_434;
            end;
            v435.apply_to_emitter = function(p436, p437) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p437)
                f_apply_simple_size_anim(p437)
                f_apply_simple_transparency_anim(p437)
                p437.Rate = 20
                p437.Texture = p436:get_image()
            end;
            return v435;
        end)()))
        local v_u_438 = "BABE PLS"
        local v_u_439 = "rbxassetid://12135431918"
        local v_u_440 = "rbxassetid://12135433070"
        v_u_17:add_fevericon_for_id(143, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_438, (copy 3): v_u_439, (copy 4): v_u_440, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v441 = v_u_5.FeverIconInfoBase:new()
            v441.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_438 ]]
                return v_u_438;
            end;
            v441.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_439 ]]
                return v_u_439;
            end;
            v441.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_440 ]]
                return v_u_440;
            end;
            v441.apply_to_emitter = function(p442, p443) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p443)
                f_apply_simple_size_anim(p443)
                f_apply_simple_transparency_anim(p443)
                p443.Rate = 20
                p443.Texture = p442:get_image()
            end;
            return v441;
        end)()))
        local v_u_444 = "chad"
        local v_u_445 = "rbxassetid://12135432073"
        local v_u_446 = "rbxassetid://12135433240"
        v_u_17:add_fevericon_for_id(144, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_444, (copy 3): v_u_445, (copy 4): v_u_446, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v447 = v_u_5.FeverIconInfoBase:new()
            v447.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_444 ]]
                return v_u_444;
            end;
            v447.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_445 ]]
                return v_u_445;
            end;
            v447.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_446 ]]
                return v_u_446;
            end;
            v447.apply_to_emitter = function(p448, p449) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p449)
                f_apply_simple_size_anim(p449)
                f_apply_simple_transparency_anim(p449)
                p449.Rate = 20
                p449.Texture = p448:get_image()
            end;
            return v447;
        end)()))
        local v_u_450 = "REBIRTH (Silentroom)"
        local v_u_451 = "rbxassetid://12263241506"
        local v_u_452 = "rbxassetid://12263241619"
        v_u_17:add_fevericon_for_id(145, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_450, (copy 3): v_u_451, (copy 4): v_u_452, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v453 = v_u_5.FeverIconInfoBase:new()
            v453.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_450 ]]
                return v_u_450;
            end;
            v453.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_451 ]]
                return v_u_451;
            end;
            v453.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_452 ]]
                return v_u_452;
            end;
            v453.apply_to_emitter = function(p454, p455) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p455)
                f_apply_simple_size_anim(p455)
                f_apply_simple_transparency_anim(p455)
                p455.Rate = 20
                p455.Texture = p454:get_image()
            end;
            return v453;
        end)()))
        local v_u_456 = "Blackmagik Blazing"
        local v_u_457 = "rbxassetid://12360891750"
        local v_u_458 = "rbxassetid://12360998603"
        v_u_17:add_fevericon_for_id(146, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_456, (copy 3): v_u_457, (copy 4): v_u_458, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v459 = v_u_5.FeverIconInfoBase:new()
            v459.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_456 ]]
                return v_u_456;
            end;
            v459.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_457 ]]
                return v_u_457;
            end;
            v459.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_458 ]]
                return v_u_458;
            end;
            v459.apply_to_emitter = function(p460, p461) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p461)
                f_apply_simple_size_anim(p461)
                f_apply_simple_transparency_anim(p461)
                p461.Rate = 20
                p461.Texture = p460:get_image()
            end;
            return v459;
        end)()))
        local v_u_462 = "Valentines Lisa"
        local v_u_463 = "rbxassetid://12414559339"
        local v_u_464 = "rbxassetid://12414559483"
        v_u_17:add_fevericon_for_id(147, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_462, (copy 3): v_u_463, (copy 4): v_u_464, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v465 = v_u_5.FeverIconInfoBase:new()
            v465.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_462 ]]
                return v_u_462;
            end;
            v465.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_463 ]]
                return v_u_463;
            end;
            v465.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_464 ]]
                return v_u_464;
            end;
            v465.apply_to_emitter = function(p466, p467) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p467)
                f_apply_simple_size_anim(p467)
                f_apply_simple_transparency_anim(p467)
                p467.Rate = 20
                p467.Texture = p466:get_image()
            end;
            return v465;
        end)()))
        local v_u_468 = "t+pazolite"
        local v_u_469 = "rbxassetid://12492606724"
        local v_u_470 = "rbxassetid://11389352283"
        v_u_17:add_fevericon_for_id(148, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_468, (copy 3): v_u_469, (copy 4): v_u_470, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v471 = v_u_5.FeverIconInfoBase:new()
            v471.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_468 ]]
                return v_u_468;
            end;
            v471.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_469 ]]
                return v_u_469;
            end;
            v471.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_470 ]]
                return v_u_470;
            end;
            v471.apply_to_emitter = function(p472, p473) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p473)
                f_apply_simple_size_anim(p473)
                f_apply_simple_transparency_anim(p473)
                p473.Rate = 20
                p473.Texture = p472:get_image()
            end;
            return v471;
        end)()))
        local v_u_474 = "mopemope"
        local v_u_475 = "rbxassetid://12663204044"
        local v_u_476 = "rbxassetid://12663204191"
        v_u_17:add_fevericon_for_id(149, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_474, (copy 3): v_u_475, (copy 4): v_u_476, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v477 = v_u_5.FeverIconInfoBase:new()
            v477.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_474 ]]
                return v_u_474;
            end;
            v477.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_475 ]]
                return v_u_475;
            end;
            v477.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_476 ]]
                return v_u_476;
            end;
            v477.apply_to_emitter = function(p478, p479) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p479)
                f_apply_simple_size_anim(p479)
                f_apply_simple_transparency_anim(p479)
                p479.Rate = 20
                p479.Texture = p478:get_image()
            end;
            return v477;
        end)()))
        local v_u_480 = "Monday Night Monsters"
        local v_u_481 = "rbxassetid://12719216469"
        local v_u_482 = "rbxassetid://12719216563"
        v_u_17:add_fevericon_for_id(150, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_480, (copy 3): v_u_481, (copy 4): v_u_482, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v483 = v_u_5.FeverIconInfoBase:new()
            v483.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_480 ]]
                return v_u_480;
            end;
            v483.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_481 ]]
                return v_u_481;
            end;
            v483.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_482 ]]
                return v_u_482;
            end;
            v483.apply_to_emitter = function(p484, p485) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p485)
                f_apply_simple_size_anim(p485)
                f_apply_simple_transparency_anim(p485)
                p485.Rate = 20
                p485.Texture = p484:get_image()
            end;
            return v483;
        end)()))
        local v_u_486 = "Pastel Emotions"
        local v_u_487 = "rbxassetid://12806497043"
        local v_u_488 = "rbxassetid://12806727813"
        v_u_17:add_fevericon_for_id(151, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_486, (copy 3): v_u_487, (copy 4): v_u_488, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v489 = v_u_5.FeverIconInfoBase:new()
            v489.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_486 ]]
                return v_u_486;
            end;
            v489.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_487 ]]
                return v_u_487;
            end;
            v489.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_488 ]]
                return v_u_488;
            end;
            v489.apply_to_emitter = function(p490, p491) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p491)
                f_apply_simple_size_anim(p491)
                f_apply_simple_transparency_anim(p491)
                p491.Rate = 20
                p491.Texture = p490:get_image()
            end;
            return v489;
        end)()))
        local v_u_492 = "Spring Mattie Selfie"
        local v_u_493 = "rbxassetid://12878202168"
        local v_u_494 = "rbxassetid://12878202235"
        v_u_17:add_fevericon_for_id(152, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_492, (copy 3): v_u_493, (copy 4): v_u_494, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v495 = v_u_5.FeverIconInfoBase:new()
            v495.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_492 ]]
                return v_u_492;
            end;
            v495.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_493 ]]
                return v_u_493;
            end;
            v495.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_494 ]]
                return v_u_494;
            end;
            v495.apply_to_emitter = function(p496, p497) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p497)
                f_apply_simple_size_anim(p497)
                f_apply_simple_transparency_anim(p497)
                p497.Rate = 20
                p497.Texture = p496:get_image()
            end;
            return v495;
        end)()))
        local v_u_498 = "8-Bit Alien"
        local v_u_499 = "rbxassetid://13015088525"
        local v_u_500 = "rbxassetid://13015088668"
        v_u_17:add_fevericon_for_id(153, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_498, (copy 3): v_u_499, (copy 4): v_u_500, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v501 = v_u_5.FeverIconInfoBase:new()
            v501.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_498 ]]
                return v_u_498;
            end;
            v501.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_499 ]]
                return v_u_499;
            end;
            v501.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_500 ]]
                return v_u_500;
            end;
            v501.apply_to_emitter = function(p502, p503) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p503)
                f_apply_simple_size_anim(p503)
                f_apply_simple_transparency_anim(p503)
                p503.Rate = 20
                p503.Texture = p502:get_image()
            end;
            return v501;
        end)()))
        local v_u_504 = "HyuN"
        local v_u_505 = "rbxassetid://13189761531"
        local v_u_506 = "rbxassetid://13189761830"
        v_u_17:add_fevericon_for_id(154, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_504, (copy 3): v_u_505, (copy 4): v_u_506, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v507 = v_u_5.FeverIconInfoBase:new()
            v507.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_504 ]]
                return v_u_504;
            end;
            v507.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_505 ]]
                return v_u_505;
            end;
            v507.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_506 ]]
                return v_u_506;
            end;
            v507.apply_to_emitter = function(p508, p509) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p509)
                f_apply_simple_size_anim(p509)
                f_apply_simple_transparency_anim(p509)
                p509.Rate = 20
                p509.Texture = p508:get_image()
            end;
            return v507;
        end)()))
        local v_u_510 = "chibi seatrus"
        local v_u_511 = "rbxassetid://11323211748"
        local v_u_512 = "rbxassetid://11323211868"
        v_u_17:add_fevericon_for_id(155, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_510, (copy 3): v_u_511, (copy 4): v_u_512, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v513 = v_u_5.FeverIconInfoBase:new()
            v513.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_510 ]]
                return v_u_510;
            end;
            v513.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_511 ]]
                return v_u_511;
            end;
            v513.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_512 ]]
                return v_u_512;
            end;
            v513.apply_to_emitter = function(p514, p515) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p515)
                f_apply_simple_size_anim(p515)
                f_apply_simple_transparency_anim(p515)
                p515.Rate = 20
                p515.Texture = p514:get_image()
            end;
            return v513;
        end)()))
        local v_u_516 = "Shiiu (Kanro)"
        local v_u_517 = "rbxassetid://13481743362"
        local v_u_518 = "rbxassetid://13481743636"
        v_u_17:add_fevericon_for_id(156, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_516, (copy 3): v_u_517, (copy 4): v_u_518, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v519 = v_u_5.FeverIconInfoBase:new()
            v519.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_516 ]]
                return v_u_516;
            end;
            v519.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_517 ]]
                return v_u_517;
            end;
            v519.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_518 ]]
                return v_u_518;
            end;
            v519.apply_to_emitter = function(p520, p521) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p521)
                f_apply_simple_size_anim(p521)
                f_apply_simple_transparency_anim(p521)
                p521.Rate = 20
                p521.Texture = p520:get_image()
            end;
            return v519;
        end)()))
        local v_u_522 = "Summer Zara"
        local v_u_523 = "rbxassetid://13745023604"
        local v_u_524 = "rbxassetid://13745023713"
        v_u_17:add_fevericon_for_id(157, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_522, (copy 3): v_u_523, (copy 4): v_u_524, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v525 = v_u_5.FeverIconInfoBase:new()
            v525.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_522 ]]
                return v_u_522;
            end;
            v525.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_523 ]]
                return v_u_523;
            end;
            v525.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_524 ]]
                return v_u_524;
            end;
            v525.apply_to_emitter = function(p526, p527) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p527)
                f_apply_simple_size_anim(p527)
                f_apply_simple_transparency_anim(p527)
                p527.Rate = 20
                p527.Texture = p526:get_image()
            end;
            return v525;
        end)()))
        local v_u_528 = "Pixel Kobaryo"
        local v_u_529 = "rbxassetid://13886118377"
        local v_u_530 = "rbxassetid://13886118516"
        v_u_17:add_fevericon_for_id(158, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_528, (copy 3): v_u_529, (copy 4): v_u_530, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v531 = v_u_5.FeverIconInfoBase:new()
            v531.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_528 ]]
                return v_u_528;
            end;
            v531.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_529 ]]
                return v_u_529;
            end;
            v531.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_530 ]]
                return v_u_530;
            end;
            v531.apply_to_emitter = function(p532, p533) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p533)
                f_apply_simple_size_anim(p533)
                f_apply_simple_transparency_anim(p533)
                p533.Rate = 20
                p533.Texture = p532:get_image()
            end;
            return v531;
        end)()))
        local v_u_534 = "Synthion"
        local v_u_535 = "rbxassetid://14056501909"
        local v_u_536 = "rbxassetid://13763581877"
        v_u_17:add_fevericon_for_id(159, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_534, (copy 3): v_u_535, (copy 4): v_u_536, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v537 = v_u_5.FeverIconInfoBase:new()
            v537.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_534 ]]
                return v_u_534;
            end;
            v537.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_535 ]]
                return v_u_535;
            end;
            v537.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_536 ]]
                return v_u_536;
            end;
            v537.apply_to_emitter = function(p538, p539) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p539)
                f_apply_simple_size_anim(p539)
                f_apply_simple_transparency_anim(p539)
                p539.Rate = 20
                p539.Texture = p538:get_image()
            end;
            return v537;
        end)()))
        local v_u_540 = "Flowering Night Fever"
        local v_u_541 = "rbxassetid://14208085396"
        local v_u_542 = "rbxassetid://14208085490"
        v_u_17:add_fevericon_for_id(160, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_540, (copy 3): v_u_541, (copy 4): v_u_542, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v543 = v_u_5.FeverIconInfoBase:new()
            v543.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_540 ]]
                return v_u_540;
            end;
            v543.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_541 ]]
                return v_u_541;
            end;
            v543.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_542 ]]
                return v_u_542;
            end;
            v543.apply_to_emitter = function(p544, p545) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p545)
                f_apply_simple_size_anim(p545)
                f_apply_simple_transparency_anim(p545)
                p545.Rate = 20
                p545.Texture = p544:get_image()
            end;
            return v543;
        end)()))
        local v_u_546 = "EmoCosine"
        local v_u_547 = "http://www.roblox.com/asset/?id=14305910184"
        local v_u_548 = "http://www.roblox.com/asset/?id=14305911527"
        v_u_17:add_fevericon_for_id(161, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_546, (copy 3): v_u_547, (copy 4): v_u_548, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v549 = v_u_5.FeverIconInfoBase:new()
            v549.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_546 ]]
                return v_u_546;
            end;
            v549.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_547 ]]
                return v_u_547;
            end;
            v549.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_548 ]]
                return v_u_548;
            end;
            v549.apply_to_emitter = function(p550, p551) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p551)
                f_apply_simple_size_anim(p551)
                f_apply_simple_transparency_anim(p551)
                p551.Rate = 20
                p551.Texture = p550:get_image()
            end;
            return v549;
        end)()))
        local v_u_552 = "I Like Balloons!"
        local v_u_553 = "rbxassetid://14475876248"
        local v_u_554 = "rbxassetid://14475876459"
        v_u_17:add_fevericon_for_id(162, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_552, (copy 3): v_u_553, (copy 4): v_u_554, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v555 = v_u_5.FeverIconInfoBase:new()
            v555.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_552 ]]
                return v_u_552;
            end;
            v555.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_553 ]]
                return v_u_553;
            end;
            v555.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_554 ]]
                return v_u_554;
            end;
            v555.apply_to_emitter = function(p556, p557) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p557)
                f_apply_simple_size_anim(p557)
                f_apply_simple_transparency_anim(p557)
                p557.Rate = 20
                p557.Texture = p556:get_image()
            end;
            return v555;
        end)()))
        local v_u_558 = "Bossfight"
        local v_u_559 = "rbxassetid://14696219579"
        local v_u_560 = "rbxassetid://14696219728"
        v_u_17:add_fevericon_for_id(163, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_558, (copy 3): v_u_559, (copy 4): v_u_560, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v561 = v_u_5.FeverIconInfoBase:new()
            v561.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_558 ]]
                return v_u_558;
            end;
            v561.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_559 ]]
                return v_u_559;
            end;
            v561.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_560 ]]
                return v_u_560;
            end;
            v561.apply_to_emitter = function(p562, p563) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p563)
                f_apply_simple_size_anim(p563)
                f_apply_simple_transparency_anim(p563)
                p563.Rate = 20
                p563.Texture = p562:get_image()
            end;
            return v561;
        end)()))
        local v_u_564 = "Bossfight Chibi"
        local v_u_565 = "rbxassetid://14696437439"
        local v_u_566 = "rbxassetid://14696437529"
        v_u_17:add_fevericon_for_id(164, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_564, (copy 3): v_u_565, (copy 4): v_u_566, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v567 = v_u_5.FeverIconInfoBase:new()
            v567.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_564 ]]
                return v_u_564;
            end;
            v567.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_565 ]]
                return v_u_565;
            end;
            v567.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_566 ]]
                return v_u_566;
            end;
            v567.apply_to_emitter = function(p568, p569) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p569)
                f_apply_simple_size_anim(p569)
                f_apply_simple_transparency_anim(p569)
                p569.Rate = 20
                p569.Texture = p568:get_image()
            end;
            return v567;
        end)()))
        local v_u_570 = "^_^"
        local v_u_571 = "rbxassetid://14835622540"
        local v_u_572 = "rbxassetid://14835622594"
        v_u_17:add_fevericon_for_id(165, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_570, (copy 3): v_u_571, (copy 4): v_u_572, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v573 = v_u_5.FeverIconInfoBase:new()
            v573.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_570 ]]
                return v_u_570;
            end;
            v573.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_571 ]]
                return v_u_571;
            end;
            v573.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_572 ]]
                return v_u_572;
            end;
            v573.apply_to_emitter = function(p574, p575) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p575)
                f_apply_simple_size_anim(p575)
                f_apply_simple_transparency_anim(p575)
                p575.Rate = 20
                p575.Texture = p574:get_image()
            end;
            return v573;
        end)()))
        local v_u_576 = "Kowloon of the Kijoh"
        local v_u_577 = "rbxassetid://14977035479"
        local v_u_578 = "rbxassetid://14977035584"
        v_u_17:add_fevericon_for_id(166, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_576, (copy 3): v_u_577, (copy 4): v_u_578, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v579 = v_u_5.FeverIconInfoBase:new()
            v579.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_576 ]]
                return v_u_576;
            end;
            v579.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_577 ]]
                return v_u_577;
            end;
            v579.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_578 ]]
                return v_u_578;
            end;
            v579.apply_to_emitter = function(p580, p581) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p581)
                f_apply_simple_size_anim(p581)
                f_apply_simple_transparency_anim(p581)
                p581.Rate = 20
                p581.Texture = p580:get_image()
            end;
            return v579;
        end)()))
        local v_u_582 = "Autumn Festival Lisa"
        local v_u_583 = "rbxassetid://15040123597"
        local v_u_584 = "rbxassetid://15040123673"
        v_u_17:add_fevericon_for_id(167, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_582, (copy 3): v_u_583, (copy 4): v_u_584, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v585 = v_u_5.FeverIconInfoBase:new()
            v585.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_582 ]]
                return v_u_582;
            end;
            v585.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_583 ]]
                return v_u_583;
            end;
            v585.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_584 ]]
                return v_u_584;
            end;
            v585.apply_to_emitter = function(p586, p587) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p587)
                f_apply_simple_size_anim(p587)
                f_apply_simple_transparency_anim(p587)
                p587.Rate = 20
                p587.Texture = p586:get_image()
            end;
            return v585;
        end)()))
        local v_u_588 = "PC Enjoyer"
        local v_u_589 = "rbxassetid://15049568106"
        local v_u_590 = "rbxassetid://15049568005"
        v_u_17:add_fevericon_for_id(168, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_588, (copy 3): v_u_589, (copy 4): v_u_590, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v591 = v_u_5.FeverIconInfoBase:new()
            v591.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_588 ]]
                return v_u_588;
            end;
            v591.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_589 ]]
                return v_u_589;
            end;
            v591.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_590 ]]
                return v_u_590;
            end;
            v591.apply_to_emitter = function(p592, p593) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p593)
                f_apply_simple_size_anim(p593)
                f_apply_simple_transparency_anim(p593)
                p593.Rate = 20
                p593.Texture = p592:get_image()
            end;
            return v591;
        end)()))
        local v_u_594 = "Mobile Enjoyer"
        local v_u_595 = "rbxassetid://15049221567"
        local v_u_596 = "rbxassetid://15049221471"
        v_u_17:add_fevericon_for_id(169, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_594, (copy 3): v_u_595, (copy 4): v_u_596, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v597 = v_u_5.FeverIconInfoBase:new()
            v597.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_594 ]]
                return v_u_594;
            end;
            v597.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_595 ]]
                return v_u_595;
            end;
            v597.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_596 ]]
                return v_u_596;
            end;
            v597.apply_to_emitter = function(p598, p599) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p599)
                f_apply_simple_size_anim(p599)
                f_apply_simple_transparency_anim(p599)
                p599.Rate = 20
                p599.Texture = p598:get_image()
            end;
            return v597;
        end)()))
        local v_u_600 = "Console Enjoyer"
        local v_u_601 = "rbxassetid://15049221669"
        local v_u_602 = "rbxassetid://15049221770"
        v_u_17:add_fevericon_for_id(170, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_600, (copy 3): v_u_601, (copy 4): v_u_602, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v603 = v_u_5.FeverIconInfoBase:new()
            v603.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_600 ]]
                return v_u_600;
            end;
            v603.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_601 ]]
                return v_u_601;
            end;
            v603.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_602 ]]
                return v_u_602;
            end;
            v603.apply_to_emitter = function(p604, p605) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p605)
                f_apply_simple_size_anim(p605)
                f_apply_simple_transparency_anim(p605)
                p605.Rate = 20
                p605.Texture = p604:get_image()
            end;
            return v603;
        end)()))
        local v_u_606 = "keisei"
        local v_u_607 = "rbxassetid://15099939897"
        local v_u_608 = "rbxassetid://15099939834"
        v_u_17:add_fevericon_for_id(171, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_606, (copy 3): v_u_607, (copy 4): v_u_608, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v609 = v_u_5.FeverIconInfoBase:new()
            v609.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_606 ]]
                return v_u_606;
            end;
            v609.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_607 ]]
                return v_u_607;
            end;
            v609.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_608 ]]
                return v_u_608;
            end;
            v609.apply_to_emitter = function(p610, p611) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p611)
                f_apply_simple_size_anim(p611)
                f_apply_simple_transparency_anim(p611)
                p611.Rate = 20
                p611.Texture = p610:get_image()
            end;
            return v609;
        end)()))
        local v_u_612 = "OOF! Kill Effect (No-Scope Arcade)"
        local v_u_613 = "rbxassetid://15247740388"
        local v_u_614 = "rbxassetid://15247740734"
        v_u_17:add_fevericon_for_id(172, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_612, (copy 3): v_u_613, (copy 4): v_u_614, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v615 = v_u_5.FeverIconInfoBase:new()
            v615.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_612 ]]
                return v_u_612;
            end;
            v615.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_613 ]]
                return v_u_613;
            end;
            v615.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_614 ]]
                return v_u_614;
            end;
            v615.apply_to_emitter = function(p616, p617) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p617)
                f_apply_simple_size_anim(p617)
                f_apply_simple_transparency_anim(p617)
                p617.Rate = 20
                p617.Texture = p616:get_image()
            end;
            return v615;
        end)()))
        local v_u_618 = "Cutter (Funo)"
        local v_u_619 = "rbxassetid://15310003883"
        local v_u_620 = "rbxassetid://15310003757"
        v_u_17:add_fevericon_for_id(173, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_618, (copy 3): v_u_619, (copy 4): v_u_620, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v621 = v_u_5.FeverIconInfoBase:new()
            v621.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_618 ]]
                return v_u_618;
            end;
            v621.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_619 ]]
                return v_u_619;
            end;
            v621.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_620 ]]
                return v_u_620;
            end;
            v621.apply_to_emitter = function(p622, p623) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p623)
                f_apply_simple_size_anim(p623)
                f_apply_simple_transparency_anim(p623)
                p623.Rate = 20
                p623.Texture = p622:get_image()
            end;
            return v621;
        end)()))
        local v_u_624 = "Sky Blue (Synthion)"
        local v_u_625 = "rbxassetid://15441010745"
        local v_u_626 = "rbxassetid://15441010612"
        v_u_17:add_fevericon_for_id(174, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_624, (copy 3): v_u_625, (copy 4): v_u_626, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v627 = v_u_5.FeverIconInfoBase:new()
            v627.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_624 ]]
                return v_u_624;
            end;
            v627.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_625 ]]
                return v_u_625;
            end;
            v627.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_626 ]]
                return v_u_626;
            end;
            v627.apply_to_emitter = function(p628, p629) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p629)
                f_apply_simple_size_anim(p629)
                f_apply_simple_transparency_anim(p629)
                p629.Rate = 20
                p629.Texture = p628:get_image()
            end;
            return v627;
        end)()))
        local v_u_630 = "Cross Over (HyuN)"
        local v_u_631 = "rbxassetid://15571201144"
        local v_u_632 = "rbxassetid://15571201024"
        v_u_17:add_fevericon_for_id(175, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_630, (copy 3): v_u_631, (copy 4): v_u_632, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v633 = v_u_5.FeverIconInfoBase:new()
            v633.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_630 ]]
                return v_u_630;
            end;
            v633.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_631 ]]
                return v_u_631;
            end;
            v633.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_632 ]]
                return v_u_632;
            end;
            v633.apply_to_emitter = function(p634, p635) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p635)
                f_apply_simple_size_anim(p635)
                f_apply_simple_transparency_anim(p635)
                p635.Rate = 20
                p635.Texture = p634:get_image()
            end;
            return v633;
        end)()))
        local v_u_636 = "Click Me! (NPC Dialog)"
        local v_u_637 = "rbxassetid://15786909330"
        local v_u_638 = "rbxassetid://15786909529"
        v_u_17:add_fevericon_for_id(176, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_636, (copy 3): v_u_637, (copy 4): v_u_638, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v639 = v_u_5.FeverIconInfoBase:new()
            v639.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_636 ]]
                return v_u_636;
            end;
            v639.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_637 ]]
                return v_u_637;
            end;
            v639.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_638 ]]
                return v_u_638;
            end;
            v639.apply_to_emitter = function(p640, p641) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p641)
                f_apply_simple_size_anim(p641)
                f_apply_simple_transparency_anim(p641)
                p641.Rate = 20
                p641.Texture = p640:get_image()
            end;
            return v639;
        end)()))
        local v_u_642 = "Juggernaut"
        local v_u_643 = "rbxassetid://15875586583"
        local v_u_644 = "rbxassetid://15875586407"
        v_u_17:add_fevericon_for_id(177, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_642, (copy 3): v_u_643, (copy 4): v_u_644, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v645 = v_u_5.FeverIconInfoBase:new()
            v645.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_642 ]]
                return v_u_642;
            end;
            v645.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_643 ]]
                return v_u_643;
            end;
            v645.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_644 ]]
                return v_u_644;
            end;
            v645.apply_to_emitter = function(p646, p647) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p647)
                f_apply_simple_size_anim(p647)
                f_apply_simple_transparency_anim(p647)
                p647.Rate = 20
                p647.Texture = p646:get_image()
            end;
            return v645;
        end)()))
        local v_u_648 = "E (seatrus)"
        local v_u_649 = "rbxassetid://16031293395"
        local v_u_650 = "rbxassetid://16031293482"
        v_u_17:add_fevericon_for_id(178, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_648, (copy 3): v_u_649, (copy 4): v_u_650, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v651 = v_u_5.FeverIconInfoBase:new()
            v651.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_648 ]]
                return v_u_648;
            end;
            v651.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_649 ]]
                return v_u_649;
            end;
            v651.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_650 ]]
                return v_u_650;
            end;
            v651.apply_to_emitter = function(p652, p653) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p653)
                f_apply_simple_size_anim(p653)
                f_apply_simple_transparency_anim(p653)
                p653.Rate = 20
                p653.Texture = p652:get_image()
            end;
            return v651;
        end)()))
        local v_u_654 = "Ops:Limone"
        local v_u_655 = "rbxassetid://16191181290"
        local v_u_656 = "rbxassetid://16191182216"
        v_u_17:add_fevericon_for_id(179, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_654, (copy 3): v_u_655, (copy 4): v_u_656, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v657 = v_u_5.FeverIconInfoBase:new()
            v657.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_654 ]]
                return v_u_654;
            end;
            v657.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_655 ]]
                return v_u_655;
            end;
            v657.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_656 ]]
                return v_u_656;
            end;
            v657.apply_to_emitter = function(p658, p659) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p659)
                f_apply_simple_size_anim(p659)
                f_apply_simple_transparency_anim(p659)
                p659.Rate = 20
                p659.Texture = p658:get_image()
            end;
            return v657;
        end)()))
        local v_u_660 = "Melty Lover"
        local v_u_661 = "rbxassetid://16291492871"
        local v_u_662 = "rbxassetid://16291492718"
        v_u_17:add_fevericon_for_id(180, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_660, (copy 3): v_u_661, (copy 4): v_u_662, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v663 = v_u_5.FeverIconInfoBase:new()
            v663.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_660 ]]
                return v_u_660;
            end;
            v663.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_661 ]]
                return v_u_661;
            end;
            v663.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_662 ]]
                return v_u_662;
            end;
            v663.apply_to_emitter = function(p664, p665) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p665)
                f_apply_simple_size_anim(p665)
                f_apply_simple_transparency_anim(p665)
                p665.Rate = 20
                p665.Texture = p664:get_image()
            end;
            return v663;
        end)()))
        local v_u_666 = "Challenge Pass Master"
        local v_u_667 = "rbxassetid://16318301142"
        local v_u_668 = "rbxassetid://16250890526"
        v_u_17:add_fevericon_for_id(181, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_666, (copy 3): v_u_667, (copy 4): v_u_668, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v669 = v_u_5.FeverIconInfoBase:new()
            v669.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_666 ]]
                return v_u_666;
            end;
            v669.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_667 ]]
                return v_u_667;
            end;
            v669.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_668 ]]
                return v_u_668;
            end;
            v669.apply_to_emitter = function(p670, p671) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p671)
                f_apply_simple_size_anim(p671)
                f_apply_simple_transparency_anim(p671)
                p671.Rate = 20
                p671.Texture = p670:get_image()
            end;
            return v669;
        end)()))
        local v_u_672 = "Hype & Love (Halv)"
        local v_u_673 = "rbxassetid://16457192333"
        local v_u_674 = "rbxassetid://16457192462"
        v_u_17:add_fevericon_for_id(182, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_672, (copy 3): v_u_673, (copy 4): v_u_674, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v675 = v_u_5.FeverIconInfoBase:new()
            v675.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_672 ]]
                return v_u_672;
            end;
            v675.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_673 ]]
                return v_u_673;
            end;
            v675.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_674 ]]
                return v_u_674;
            end;
            v675.apply_to_emitter = function(p676, p677) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p677)
                f_apply_simple_size_anim(p677)
                f_apply_simple_transparency_anim(p677)
                p677.Rate = 20
                p677.Texture = p676:get_image()
            end;
            return v675;
        end)()))
        local v_u_678 = "Point"
        local v_u_679 = "rbxassetid://16662304998"
        local v_u_680 = "rbxassetid://16662298258"
        v_u_17:add_fevericon_for_id(183, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_678, (copy 3): v_u_679, (copy 4): v_u_680, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v681 = v_u_5.FeverIconInfoBase:new()
            v681.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_678 ]]
                return v_u_678;
            end;
            v681.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_679 ]]
                return v_u_679;
            end;
            v681.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_680 ]]
                return v_u_680;
            end;
            v681.apply_to_emitter = function(p682, p683) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p683)
                f_apply_simple_size_anim(p683)
                f_apply_simple_transparency_anim(p683)
                p683.Rate = 20
                p683.Texture = p682:get_image()
            end;
            return v681;
        end)()))
        local v_u_684 = "Gun"
        local v_u_685 = "rbxassetid://16662305059"
        local v_u_686 = "rbxassetid://16662298361"
        v_u_17:add_fevericon_for_id(184, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_684, (copy 3): v_u_685, (copy 4): v_u_686, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v687 = v_u_5.FeverIconInfoBase:new()
            v687.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_684 ]]
                return v_u_684;
            end;
            v687.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_685 ]]
                return v_u_685;
            end;
            v687.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_686 ]]
                return v_u_686;
            end;
            v687.apply_to_emitter = function(p688, p689) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p689)
                f_apply_simple_size_anim(p689)
                f_apply_simple_transparency_anim(p689)
                p689.Rate = 20
                p689.Texture = p688:get_image()
            end;
            return v687;
        end)()))
        local v_u_690 = "Gentlemanly"
        local v_u_691 = "rbxassetid://16662305165"
        local v_u_692 = "rbxassetid://16662298541"
        v_u_17:add_fevericon_for_id(185, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_690, (copy 3): v_u_691, (copy 4): v_u_692, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v693 = v_u_5.FeverIconInfoBase:new()
            v693.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_690 ]]
                return v_u_690;
            end;
            v693.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_691 ]]
                return v_u_691;
            end;
            v693.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_692 ]]
                return v_u_692;
            end;
            v693.apply_to_emitter = function(p694, p695) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p695)
                f_apply_simple_size_anim(p695)
                f_apply_simple_transparency_anim(p695)
                p695.Rate = 20
                p695.Texture = p694:get_image()
            end;
            return v693;
        end)()))
        local v_u_696 = "Is For Me?"
        local v_u_697 = "rbxassetid://16662305362"
        local v_u_698 = "rbxassetid://16662298701"
        v_u_17:add_fevericon_for_id(186, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_696, (copy 3): v_u_697, (copy 4): v_u_698, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v699 = v_u_5.FeverIconInfoBase:new()
            v699.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_696 ]]
                return v_u_696;
            end;
            v699.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_697 ]]
                return v_u_697;
            end;
            v699.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_698 ]]
                return v_u_698;
            end;
            v699.apply_to_emitter = function(p700, p701) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p701)
                f_apply_simple_size_anim(p701)
                f_apply_simple_transparency_anim(p701)
                p701.Rate = 20
                p701.Texture = p700:get_image()
            end;
            return v699;
        end)()))
        local v_u_702 = "Sweating..."
        local v_u_703 = "rbxassetid://16662305557"
        local v_u_704 = "rbxassetid://16662298903"
        v_u_17:add_fevericon_for_id(187, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_702, (copy 3): v_u_703, (copy 4): v_u_704, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v705 = v_u_5.FeverIconInfoBase:new()
            v705.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_702 ]]
                return v_u_702;
            end;
            v705.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_703 ]]
                return v_u_703;
            end;
            v705.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_704 ]]
                return v_u_704;
            end;
            v705.apply_to_emitter = function(p706, p707) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p707)
                f_apply_simple_size_anim(p707)
                f_apply_simple_transparency_anim(p707)
                p707.Rate = 20
                p707.Texture = p706:get_image()
            end;
            return v705;
        end)()))
        local v_u_708 = "Hot..."
        local v_u_709 = "rbxassetid://16662311839"
        local v_u_710 = "rbxassetid://16662299158"
        v_u_17:add_fevericon_for_id(188, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_708, (copy 3): v_u_709, (copy 4): v_u_710, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v711 = v_u_5.FeverIconInfoBase:new()
            v711.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_708 ]]
                return v_u_708;
            end;
            v711.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_709 ]]
                return v_u_709;
            end;
            v711.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_710 ]]
                return v_u_710;
            end;
            v711.apply_to_emitter = function(p712, p713) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p713)
                f_apply_simple_size_anim(p713)
                f_apply_simple_transparency_anim(p713)
                p713.Rate = 20
                p713.Texture = p712:get_image()
            end;
            return v711;
        end)()))
        local v_u_714 = ":D"
        local v_u_715 = "rbxassetid://16662311994"
        local v_u_716 = "rbxassetid://16662304900"
        v_u_17:add_fevericon_for_id(189, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_714, (copy 3): v_u_715, (copy 4): v_u_716, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v717 = v_u_5.FeverIconInfoBase:new()
            v717.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_714 ]]
                return v_u_714;
            end;
            v717.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_715 ]]
                return v_u_715;
            end;
            v717.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_716 ]]
                return v_u_716;
            end;
            v717.apply_to_emitter = function(p718, p719) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p719)
                f_apply_simple_size_anim(p719)
                f_apply_simple_transparency_anim(p719)
                p719.Rate = 20
                p719.Texture = p718:get_image()
            end;
            return v717;
        end)()))
        local v_u_720 = "Helium"
        local v_u_721 = "rbxassetid://16746856043"
        local v_u_722 = "rbxassetid://16746855950"
        v_u_17:add_fevericon_for_id(190, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_720, (copy 3): v_u_721, (copy 4): v_u_722, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v723 = v_u_5.FeverIconInfoBase:new()
            v723.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_720 ]]
                return v_u_720;
            end;
            v723.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_721 ]]
                return v_u_721;
            end;
            v723.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_722 ]]
                return v_u_722;
            end;
            v723.apply_to_emitter = function(p724, p725) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p725)
                f_apply_simple_size_anim(p725)
                f_apply_simple_transparency_anim(p725)
                p725.Rate = 20
                p725.Texture = p724:get_image()
            end;
            return v723;
        end)()))
        local v_u_726 = "Starry Night & A Single Flower"
        local v_u_727 = "rbxassetid://16900621066"
        local v_u_728 = "rbxassetid://16900621289"
        v_u_17:add_fevericon_for_id(191, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_726, (copy 3): v_u_727, (copy 4): v_u_728, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v729 = v_u_5.FeverIconInfoBase:new()
            v729.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_726 ]]
                return v_u_726;
            end;
            v729.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_727 ]]
                return v_u_727;
            end;
            v729.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_728 ]]
                return v_u_728;
            end;
            v729.apply_to_emitter = function(p730, p731) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p731)
                f_apply_simple_size_anim(p731)
                f_apply_simple_transparency_anim(p731)
                p731.Rate = 20
                p731.Texture = p730:get_image()
            end;
            return v729;
        end)()))
        local v_u_732 = "you"
        local v_u_733 = "rbxassetid://17087355525"
        local v_u_734 = "rbxassetid://17087355770"
        v_u_17:add_fevericon_for_id(192, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_732, (copy 3): v_u_733, (copy 4): v_u_734, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v735 = v_u_5.FeverIconInfoBase:new()
            v735.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_732 ]]
                return v_u_732;
            end;
            v735.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_733 ]]
                return v_u_733;
            end;
            v735.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_734 ]]
                return v_u_734;
            end;
            v735.apply_to_emitter = function(p736, p737) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p737)
                f_apply_simple_size_anim(p737)
                f_apply_simple_transparency_anim(p737)
                p737.Rate = 20
                p737.Texture = p736:get_image()
            end;
            return v735;
        end)()))
        local v_u_738 = "Apocalypse Survivor Starlet"
        local v_u_739 = "rbxassetid://17269684389"
        local v_u_740 = "rbxassetid://17269684289"
        v_u_17:add_fevericon_for_id(193, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_738, (copy 3): v_u_739, (copy 4): v_u_740, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v741 = v_u_5.FeverIconInfoBase:new()
            v741.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_738 ]]
                return v_u_738;
            end;
            v741.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_739 ]]
                return v_u_739;
            end;
            v741.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_740 ]]
                return v_u_740;
            end;
            v741.apply_to_emitter = function(p742, p743) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p743)
                f_apply_simple_size_anim(p743)
                f_apply_simple_transparency_anim(p743)
                p743.Rate = 20
                p743.Texture = p742:get_image()
            end;
            return v741;
        end)()))
        local v_u_744 = "Project Skylate"
        local v_u_745 = "rbxassetid://17440162403"
        local v_u_746 = "rbxassetid://17440162252"
        v_u_17:add_fevericon_for_id(194, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_744, (copy 3): v_u_745, (copy 4): v_u_746, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v747 = v_u_5.FeverIconInfoBase:new()
            v747.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_744 ]]
                return v_u_744;
            end;
            v747.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_745 ]]
                return v_u_745;
            end;
            v747.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_746 ]]
                return v_u_746;
            end;
            v747.apply_to_emitter = function(p748, p749) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p749)
                f_apply_simple_size_anim(p749)
                f_apply_simple_transparency_anim(p749)
                p749.Rate = 20
                p749.Texture = p748:get_image()
            end;
            return v747;
        end)()))
        local v_u_750 = "Remember (Juggernaut)"
        local v_u_751 = "rbxassetid://17591638288"
        local v_u_752 = "rbxassetid://17591638190"
        v_u_17:add_fevericon_for_id(195, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_750, (copy 3): v_u_751, (copy 4): v_u_752, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v753 = v_u_5.FeverIconInfoBase:new()
            v753.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_750 ]]
                return v_u_750;
            end;
            v753.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_751 ]]
                return v_u_751;
            end;
            v753.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_752 ]]
                return v_u_752;
            end;
            v753.apply_to_emitter = function(p754, p755) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p755)
                f_apply_simple_size_anim(p755)
                f_apply_simple_transparency_anim(p755)
                p755.Rate = 20
                p755.Texture = p754:get_image()
            end;
            return v753;
        end)()))
        local v_u_756 = "AAAA"
        local v_u_757 = "rbxassetid://17737244011"
        local v_u_758 = "rbxassetid://17737244481"
        v_u_17:add_fevericon_for_id(196, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_756, (copy 3): v_u_757, (copy 4): v_u_758, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v759 = v_u_5.FeverIconInfoBase:new()
            v759.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_756 ]]
                return v_u_756;
            end;
            v759.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_757 ]]
                return v_u_757;
            end;
            v759.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_758 ]]
                return v_u_758;
            end;
            v759.apply_to_emitter = function(p760, p761) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p761)
                f_apply_simple_size_anim(p761)
                f_apply_simple_transparency_anim(p761)
                p761.Rate = 20
                p761.Texture = p760:get_image()
            end;
            return v759;
        end)()))
        local v_u_762 = "Memory of Summer (Halv)"
        local v_u_763 = "rbxassetid://18102158838"
        local v_u_764 = "rbxassetid://18102158970"
        v_u_17:add_fevericon_for_id(197, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_762, (copy 3): v_u_763, (copy 4): v_u_764, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v765 = v_u_5.FeverIconInfoBase:new()
            v765.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_762 ]]
                return v_u_762;
            end;
            v765.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_763 ]]
                return v_u_763;
            end;
            v765.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_764 ]]
                return v_u_764;
            end;
            v765.apply_to_emitter = function(p766, p767) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p767)
                f_apply_simple_size_anim(p767)
                f_apply_simple_transparency_anim(p767)
                p767.Rate = 20
                p767.Texture = p766:get_image()
            end;
            return v765;
        end)()))
        local v_u_768 = "Onigiri"
        local v_u_769 = "rbxassetid://18333884853"
        local v_u_770 = "rbxassetid://18333884684"
        v_u_17:add_fevericon_for_id(198, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_768, (copy 3): v_u_769, (copy 4): v_u_770, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v771 = v_u_5.FeverIconInfoBase:new()
            v771.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_768 ]]
                return v_u_768;
            end;
            v771.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_769 ]]
                return v_u_769;
            end;
            v771.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_770 ]]
                return v_u_770;
            end;
            v771.apply_to_emitter = function(p772, p773) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p773)
                f_apply_simple_size_anim(p773)
                f_apply_simple_transparency_anim(p773)
                p773.Rate = 20
                p773.Texture = p772:get_image()
            end;
            return v771;
        end)()))
        local v_u_774 = "Kagetora"
        local v_u_775 = "rbxassetid://18524512644"
        local v_u_776 = "rbxassetid://18524512790"
        v_u_17:add_fevericon_for_id(199, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_774, (copy 3): v_u_775, (copy 4): v_u_776, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v777 = v_u_5.FeverIconInfoBase:new()
            v777.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_774 ]]
                return v_u_774;
            end;
            v777.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_775 ]]
                return v_u_775;
            end;
            v777.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_776 ]]
                return v_u_776;
            end;
            v777.apply_to_emitter = function(p778, p779) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p779)
                f_apply_simple_size_anim(p779)
                f_apply_simple_transparency_anim(p779)
                p779.Rate = 20
                p779.Texture = p778:get_image()
            end;
            return v777;
        end)()))
        local v_u_780 = "The Games"
        local v_u_781 = "rbxassetid://18686397650"
        local v_u_782 = "rbxassetid://18686397838"
        v_u_17:add_fevericon_for_id(200, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_780, (copy 3): v_u_781, (copy 4): v_u_782, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v783 = v_u_5.FeverIconInfoBase:new()
            v783.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_780 ]]
                return v_u_780;
            end;
            v783.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_781 ]]
                return v_u_781;
            end;
            v783.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_782 ]]
                return v_u_782;
            end;
            v783.apply_to_emitter = function(p784, p785) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p785)
                f_apply_simple_size_anim(p785)
                f_apply_simple_transparency_anim(p785)
                p785.Rate = 20
                p785.Texture = p784:get_image()
            end;
            return v783;
        end)()))
        local v_u_786 = "USAO"
        local v_u_787 = "rbxassetid://18963806184"
        local v_u_788 = "rbxassetid://18963805981"
        v_u_17:add_fevericon_for_id(201, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_786, (copy 3): v_u_787, (copy 4): v_u_788, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v789 = v_u_5.FeverIconInfoBase:new()
            v789.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_786 ]]
                return v_u_786;
            end;
            v789.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_787 ]]
                return v_u_787;
            end;
            v789.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_788 ]]
                return v_u_788;
            end;
            v789.apply_to_emitter = function(p790, p791) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p791)
                f_apply_simple_size_anim(p791)
                f_apply_simple_transparency_anim(p791)
                p791.Rate = 20
                p791.Texture = p790:get_image()
            end;
            return v789;
        end)()))
        local v_u_792 = "Pet Rock"
        local v_u_793 = "rbxassetid://96353839272305"
        local v_u_794 = "rbxassetid://98789409467278"
        v_u_17:add_fevericon_for_id(202, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_792, (copy 3): v_u_793, (copy 4): v_u_794, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v795 = v_u_5.FeverIconInfoBase:new()
            v795.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_792 ]]
                return v_u_792;
            end;
            v795.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_793 ]]
                return v_u_793;
            end;
            v795.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_794 ]]
                return v_u_794;
            end;
            v795.apply_to_emitter = function(p796, p797) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p797)
                f_apply_simple_size_anim(p797)
                f_apply_simple_transparency_anim(p797)
                p797.Rate = 20
                p797.Texture = p796:get_image()
            end;
            return v795;
        end)()))
        local v_u_798 = "Hello Darkness"
        local v_u_799 = "rbxassetid://77074352849680"
        local v_u_800 = "rbxassetid://117802115600921"
        v_u_17:add_fevericon_for_id(203, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_798, (copy 3): v_u_799, (copy 4): v_u_800, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v801 = v_u_5.FeverIconInfoBase:new()
            v801.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_798 ]]
                return v_u_798;
            end;
            v801.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_799 ]]
                return v_u_799;
            end;
            v801.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_800 ]]
                return v_u_800;
            end;
            v801.apply_to_emitter = function(p802, p803) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p803)
                f_apply_simple_size_anim(p803)
                f_apply_simple_transparency_anim(p803)
                p803.Rate = 20
                p803.Texture = p802:get_image()
            end;
            return v801;
        end)()))
        local v_u_804 = "Fren"
        local v_u_805 = "rbxassetid://77183409007761"
        local v_u_806 = "rbxassetid://118910207569067"
        v_u_17:add_fevericon_for_id(204, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_804, (copy 3): v_u_805, (copy 4): v_u_806, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v807 = v_u_5.FeverIconInfoBase:new()
            v807.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_804 ]]
                return v_u_804;
            end;
            v807.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_805 ]]
                return v_u_805;
            end;
            v807.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_806 ]]
                return v_u_806;
            end;
            v807.apply_to_emitter = function(p808, p809) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p809)
                f_apply_simple_size_anim(p809)
                f_apply_simple_transparency_anim(p809)
                p809.Rate = 20
                p809.Texture = p808:get_image()
            end;
            return v807;
        end)()))
        local v_u_810 = "Cooked"
        local v_u_811 = "rbxassetid://82949456393126"
        local v_u_812 = "rbxassetid://97592262206966"
        v_u_17:add_fevericon_for_id(205, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_810, (copy 3): v_u_811, (copy 4): v_u_812, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v813 = v_u_5.FeverIconInfoBase:new()
            v813.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_810 ]]
                return v_u_810;
            end;
            v813.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_811 ]]
                return v_u_811;
            end;
            v813.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_812 ]]
                return v_u_812;
            end;
            v813.apply_to_emitter = function(p814, p815) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p815)
                f_apply_simple_size_anim(p815)
                f_apply_simple_transparency_anim(p815)
                p815.Rate = 20
                p815.Texture = p814:get_image()
            end;
            return v813;
        end)()))
        local v_u_816 = "Running Dad"
        local v_u_817 = "rbxassetid://135455188972381"
        local v_u_818 = "rbxassetid://75231387104564"
        v_u_17:add_fevericon_for_id(206, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_816, (copy 3): v_u_817, (copy 4): v_u_818, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v819 = v_u_5.FeverIconInfoBase:new()
            v819.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_816 ]]
                return v_u_816;
            end;
            v819.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_817 ]]
                return v_u_817;
            end;
            v819.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_818 ]]
                return v_u_818;
            end;
            v819.apply_to_emitter = function(p820, p821) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p821)
                f_apply_simple_size_anim(p821)
                f_apply_simple_transparency_anim(p821)
                p821.Rate = 20
                p821.Texture = p820:get_image()
            end;
            return v819;
        end)()))
        local v_u_822 = "Wheeze"
        local v_u_823 = "rbxassetid://108462445268515"
        local v_u_824 = "rbxassetid://86912894782539"
        v_u_17:add_fevericon_for_id(207, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_822, (copy 3): v_u_823, (copy 4): v_u_824, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v825 = v_u_5.FeverIconInfoBase:new()
            v825.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_822 ]]
                return v_u_822;
            end;
            v825.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_823 ]]
                return v_u_823;
            end;
            v825.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_824 ]]
                return v_u_824;
            end;
            v825.apply_to_emitter = function(p826, p827) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p827)
                f_apply_simple_size_anim(p827)
                f_apply_simple_transparency_anim(p827)
                p827.Rate = 20
                p827.Texture = p826:get_image()
            end;
            return v825;
        end)()))
        local v_u_828 = "I Wake Up"
        local v_u_829 = "rbxassetid://102266343588334"
        local v_u_830 = "rbxassetid://106634824093393"
        v_u_17:add_fevericon_for_id(208, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_828, (copy 3): v_u_829, (copy 4): v_u_830, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v831 = v_u_5.FeverIconInfoBase:new()
            v831.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_828 ]]
                return v_u_828;
            end;
            v831.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_829 ]]
                return v_u_829;
            end;
            v831.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_830 ]]
                return v_u_830;
            end;
            v831.apply_to_emitter = function(p832, p833) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p833)
                f_apply_simple_size_anim(p833)
                f_apply_simple_transparency_anim(p833)
                p833.Rate = 20
                p833.Texture = p832:get_image()
            end;
            return v831;
        end)()))
        local v_u_834 = "Hokusai"
        local v_u_835 = "rbxassetid://133335020815188"
        local v_u_836 = "rbxassetid://100008486774639"
        v_u_17:add_fevericon_for_id(209, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_834, (copy 3): v_u_835, (copy 4): v_u_836, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v837 = v_u_5.FeverIconInfoBase:new()
            v837.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_834 ]]
                return v_u_834;
            end;
            v837.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_835 ]]
                return v_u_835;
            end;
            v837.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_836 ]]
                return v_u_836;
            end;
            v837.apply_to_emitter = function(p838, p839) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p839)
                f_apply_simple_size_anim(p839)
                f_apply_simple_transparency_anim(p839)
                p839.Rate = 20
                p839.Texture = p838:get_image()
            end;
            return v837;
        end)()))
        local v_u_840 = "Coolest Thing Ever"
        local v_u_841 = "rbxassetid://128694571112311"
        local v_u_842 = "rbxassetid://106013989100027"
        v_u_17:add_fevericon_for_id(210, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_840, (copy 3): v_u_841, (copy 4): v_u_842, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v843 = v_u_5.FeverIconInfoBase:new()
            v843.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_840 ]]
                return v_u_840;
            end;
            v843.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_841 ]]
                return v_u_841;
            end;
            v843.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_842 ]]
                return v_u_842;
            end;
            v843.apply_to_emitter = function(p844, p845) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p845)
                f_apply_simple_size_anim(p845)
                f_apply_simple_transparency_anim(p845)
                p845.Rate = 20
                p845.Texture = p844:get_image()
            end;
            return v843;
        end)()))
        local v_u_846 = "Bubble Beam (nanobii)"
        local v_u_847 = "rbxassetid://89716916252989"
        local v_u_848 = "rbxassetid://125565568920226"
        v_u_17:add_fevericon_for_id(211, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_846, (copy 3): v_u_847, (copy 4): v_u_848, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v849 = v_u_5.FeverIconInfoBase:new()
            v849.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_846 ]]
                return v_u_846;
            end;
            v849.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_847 ]]
                return v_u_847;
            end;
            v849.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_848 ]]
                return v_u_848;
            end;
            v849.apply_to_emitter = function(p850, p851) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p851)
                f_apply_simple_size_anim(p851)
                f_apply_simple_transparency_anim(p851)
                p851.Rate = 20
                p851.Texture = p850:get_image()
            end;
            return v849;
        end)()))
        local v_u_852 = "Yesterwynde"
        local v_u_853 = "rbxassetid://83568739177434"
        local v_u_854 = "rbxassetid://113395566661924"
        v_u_17:add_fevericon_for_id(212, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_852, (copy 3): v_u_853, (copy 4): v_u_854, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v855 = v_u_5.FeverIconInfoBase:new()
            v855.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_852 ]]
                return v_u_852;
            end;
            v855.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_853 ]]
                return v_u_853;
            end;
            v855.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_854 ]]
                return v_u_854;
            end;
            v855.apply_to_emitter = function(p856, p857) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p857)
                f_apply_simple_size_anim(p857)
                f_apply_simple_transparency_anim(p857)
                p857.Rate = 20
                p857.Texture = p856:get_image()
            end;
            return v855;
        end)()))
        local v_u_858 = "Autumn Lisa (OwEnigma)"
        local v_u_859 = "rbxassetid://74680195148968"
        local v_u_860 = "rbxassetid://137687138604255"
        v_u_17:add_fevericon_for_id(213, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_858, (copy 3): v_u_859, (copy 4): v_u_860, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v861 = v_u_5.FeverIconInfoBase:new()
            v861.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_858 ]]
                return v_u_858;
            end;
            v861.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_859 ]]
                return v_u_859;
            end;
            v861.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_860 ]]
                return v_u_860;
            end;
            v861.apply_to_emitter = function(p862, p863) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p863)
                f_apply_simple_size_anim(p863)
                f_apply_simple_transparency_anim(p863)
                p863.Rate = 20
                p863.Texture = p862:get_image()
            end;
            return v861;
        end)()))
        local v_u_864 = "Brilliant & Shining! (Halv)"
        local v_u_865 = "rbxassetid://84000438829967"
        local v_u_866 = "rbxassetid://72848731727311"
        v_u_17:add_fevericon_for_id(214, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_864, (copy 3): v_u_865, (copy 4): v_u_866, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v867 = v_u_5.FeverIconInfoBase:new()
            v867.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_864 ]]
                return v_u_864;
            end;
            v867.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_865 ]]
                return v_u_865;
            end;
            v867.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_866 ]]
                return v_u_866;
            end;
            v867.apply_to_emitter = function(p868, p869) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p869)
                f_apply_simple_size_anim(p869)
                f_apply_simple_transparency_anim(p869)
                p869.Rate = 20
                p869.Texture = p868:get_image()
            end;
            return v867;
        end)()))
        local v_u_870 = "Skylate Halloween"
        local v_u_871 = "rbxassetid://71110259683642"
        local v_u_872 = "rbxassetid://87206248678460"
        v_u_17:add_fevericon_for_id(215, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_870, (copy 3): v_u_871, (copy 4): v_u_872, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v873 = v_u_5.FeverIconInfoBase:new()
            v873.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_870 ]]
                return v_u_870;
            end;
            v873.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_871 ]]
                return v_u_871;
            end;
            v873.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_872 ]]
                return v_u_872;
            end;
            v873.apply_to_emitter = function(p874, p875) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p875)
                f_apply_simple_size_anim(p875)
                f_apply_simple_transparency_anim(p875)
                p875.Rate = 20
                p875.Texture = p874:get_image()
            end;
            return v873;
        end)()))
        local v_u_876 = "Black17"
        local v_u_877 = "rbxassetid://135275511671602"
        local v_u_878 = "rbxassetid://109928910776634"
        v_u_17:add_fevericon_for_id(216, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_876, (copy 3): v_u_877, (copy 4): v_u_878, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v879 = v_u_5.FeverIconInfoBase:new()
            v879.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_876 ]]
                return v_u_876;
            end;
            v879.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_877 ]]
                return v_u_877;
            end;
            v879.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_878 ]]
                return v_u_878;
            end;
            v879.apply_to_emitter = function(p880, p881) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p881)
                f_apply_simple_size_anim(p881)
                f_apply_simple_transparency_anim(p881)
                p881.Rate = 20
                p881.Texture = p880:get_image()
            end;
            return v879;
        end)()))
        local v_u_882 = "YooH"
        local v_u_883 = "rbxassetid://95853128601674"
        local v_u_884 = "rbxassetid://74689269460765"
        v_u_17:add_fevericon_for_id(217, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_882, (copy 3): v_u_883, (copy 4): v_u_884, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v885 = v_u_5.FeverIconInfoBase:new()
            v885.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_882 ]]
                return v_u_882;
            end;
            v885.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_883 ]]
                return v_u_883;
            end;
            v885.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_884 ]]
                return v_u_884;
            end;
            v885.apply_to_emitter = function(p886, p887) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p887)
                f_apply_simple_size_anim(p887)
                f_apply_simple_transparency_anim(p887)
                p887.Rate = 20
                p887.Texture = p886:get_image()
            end;
            return v885;
        end)()))
        local v_u_888 = "Let\'s Jump! (you)"
        local v_u_889 = "rbxassetid://120733473959523"
        local v_u_890 = "rbxassetid://103890248618191"
        v_u_17:add_fevericon_for_id(218, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_888, (copy 3): v_u_889, (copy 4): v_u_890, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v891 = v_u_5.FeverIconInfoBase:new()
            v891.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_888 ]]
                return v_u_888;
            end;
            v891.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_889 ]]
                return v_u_889;
            end;
            v891.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_890 ]]
                return v_u_890;
            end;
            v891.apply_to_emitter = function(p892, p893) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p893)
                f_apply_simple_size_anim(p893)
                f_apply_simple_transparency_anim(p893)
                p893.Rate = 20
                p893.Texture = p892:get_image()
            end;
            return v891;
        end)()))
        local v_u_894 = "Santa\'s Helper Marsha (OwEnigma)"
        local v_u_895 = "rbxassetid://106852236666738"
        local v_u_896 = "rbxassetid://107504664518711"
        v_u_17:add_fevericon_for_id(219, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_894, (copy 3): v_u_895, (copy 4): v_u_896, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v897 = v_u_5.FeverIconInfoBase:new()
            v897.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_894 ]]
                return v_u_894;
            end;
            v897.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_895 ]]
                return v_u_895;
            end;
            v897.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_896 ]]
                return v_u_896;
            end;
            v897.apply_to_emitter = function(p898, p899) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p899)
                f_apply_simple_size_anim(p899)
                f_apply_simple_transparency_anim(p899)
                p899.Rate = 20
                p899.Texture = p898:get_image()
            end;
            return v897;
        end)()))
        local v_u_900 = "Snail\'s House"
        local v_u_901 = "rbxassetid://123006991479228"
        local v_u_902 = "rbxassetid://93065950225614"
        v_u_17:add_fevericon_for_id(220, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_900, (copy 3): v_u_901, (copy 4): v_u_902, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v903 = v_u_5.FeverIconInfoBase:new()
            v903.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_900 ]]
                return v_u_900;
            end;
            v903.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_901 ]]
                return v_u_901;
            end;
            v903.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_902 ]]
                return v_u_902;
            end;
            v903.apply_to_emitter = function(p904, p905) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p905)
                f_apply_simple_size_anim(p905)
                f_apply_simple_transparency_anim(p905)
                p905.Rate = 20
                p905.Texture = p904:get_image()
            end;
            return v903;
        end)()))
        local v_u_906 = "Halfduck"
        local v_u_907 = "rbxassetid://91591576937601"
        local v_u_908 = "rbxassetid://132146960780538"
        v_u_17:add_fevericon_for_id(221, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_906, (copy 3): v_u_907, (copy 4): v_u_908, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v909 = v_u_5.FeverIconInfoBase:new()
            v909.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_906 ]]
                return v_u_906;
            end;
            v909.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_907 ]]
                return v_u_907;
            end;
            v909.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_908 ]]
                return v_u_908;
            end;
            v909.apply_to_emitter = function(p910, p911) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p911)
                f_apply_simple_size_anim(p911)
                f_apply_simple_transparency_anim(p911)
                p911.Rate = 20
                p911.Texture = p910:get_image()
            end;
            return v909;
        end)()))
        local v_u_912 = "Valentines Lisa (OwEnigma)"
        local v_u_913 = "rbxassetid://124901049358015"
        local v_u_914 = "rbxassetid://95060131126427"
        v_u_17:add_fevericon_for_id(222, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_912, (copy 3): v_u_913, (copy 4): v_u_914, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v915 = v_u_5.FeverIconInfoBase:new()
            v915.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_912 ]]
                return v_u_912;
            end;
            v915.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_913 ]]
                return v_u_913;
            end;
            v915.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_914 ]]
                return v_u_914;
            end;
            v915.apply_to_emitter = function(p916, p917) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p917)
                f_apply_simple_size_anim(p917)
                f_apply_simple_transparency_anim(p917)
                p917.Rate = 20
                p917.Texture = p916:get_image()
            end;
            return v915;
        end)()))
        local v_u_918 = "Sad Hamster"
        local v_u_919 = "rbxassetid://82042564543617"
        local v_u_920 = "rbxassetid://71621921638752"
        v_u_17:add_fevericon_for_id(223, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_918, (copy 3): v_u_919, (copy 4): v_u_920, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v921 = v_u_5.FeverIconInfoBase:new()
            v921.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_918 ]]
                return v_u_918;
            end;
            v921.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_919 ]]
                return v_u_919;
            end;
            v921.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_920 ]]
                return v_u_920;
            end;
            v921.apply_to_emitter = function(p922, p923) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p923)
                f_apply_simple_size_anim(p923)
                f_apply_simple_transparency_anim(p923)
                p923.Rate = 20
                p923.Texture = p922:get_image()
            end;
            return v921;
        end)()))
        local v_u_924 = "Fusq"
        local v_u_925 = "rbxassetid://102991461560091"
        local v_u_926 = "rbxassetid://124083396965248"
        v_u_17:add_fevericon_for_id(224, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_924, (copy 3): v_u_925, (copy 4): v_u_926, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v927 = v_u_5.FeverIconInfoBase:new()
            v927.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_924 ]]
                return v_u_924;
            end;
            v927.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_925 ]]
                return v_u_925;
            end;
            v927.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_926 ]]
                return v_u_926;
            end;
            v927.apply_to_emitter = function(p928, p929) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p929)
                f_apply_simple_size_anim(p929)
                f_apply_simple_transparency_anim(p929)
                p929.Rate = 20
                p929.Texture = p928:get_image()
            end;
            return v927;
        end)()))
        local v_u_930 = "Hanami Dango (AAAA)"
        local v_u_931 = "rbxassetid://113818245569172"
        local v_u_932 = "rbxassetid://108169762757593"
        v_u_17:add_fevericon_for_id(225, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_930, (copy 3): v_u_931, (copy 4): v_u_932, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v933 = v_u_5.FeverIconInfoBase:new()
            v933.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_930 ]]
                return v_u_930;
            end;
            v933.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_931 ]]
                return v_u_931;
            end;
            v933.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_932 ]]
                return v_u_932;
            end;
            v933.apply_to_emitter = function(p934, p935) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p935)
                f_apply_simple_size_anim(p935)
                f_apply_simple_transparency_anim(p935)
                p935.Rate = 20
                p935.Texture = p934:get_image()
            end;
            return v933;
        end)()))
        local v_u_936 = "Lappy"
        local v_u_937 = "rbxassetid://121125880015695"
        local v_u_938 = "rbxassetid://73951460269568"
        v_u_17:add_fevericon_for_id(226, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_936, (copy 3): v_u_937, (copy 4): v_u_938, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v939 = v_u_5.FeverIconInfoBase:new()
            v939.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_936 ]]
                return v_u_936;
            end;
            v939.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_937 ]]
                return v_u_937;
            end;
            v939.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_938 ]]
                return v_u_938;
            end;
            v939.apply_to_emitter = function(p940, p941) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p941)
                f_apply_simple_size_anim(p941)
                f_apply_simple_transparency_anim(p941)
                p941.Rate = 20
                p941.Texture = p940:get_image()
            end;
            return v939;
        end)()))
        local v_u_942 = "Headspace (Similar Outskirts)"
        local v_u_943 = "rbxassetid://92705388191887"
        local v_u_944 = "rbxassetid://79870444250125"
        v_u_17:add_fevericon_for_id(227, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_942, (copy 3): v_u_943, (copy 4): v_u_944, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v945 = v_u_5.FeverIconInfoBase:new()
            v945.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_942 ]]
                return v_u_942;
            end;
            v945.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_943 ]]
                return v_u_943;
            end;
            v945.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_944 ]]
                return v_u_944;
            end;
            v945.apply_to_emitter = function(p946, p947) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p947)
                f_apply_simple_size_anim(p947)
                f_apply_simple_transparency_anim(p947)
                p947.Rate = 20
                p947.Texture = p946:get_image()
            end;
            return v945;
        end)()))
        local v_u_948 = "Untitled Soul"
        local v_u_949 = "rbxassetid://82864960902434"
        local v_u_950 = "rbxassetid://84353025132612"
        v_u_17:add_fevericon_for_id(228, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_948, (copy 3): v_u_949, (copy 4): v_u_950, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v951 = v_u_5.FeverIconInfoBase:new()
            v951.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_948 ]]
                return v_u_948;
            end;
            v951.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_949 ]]
                return v_u_949;
            end;
            v951.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_950 ]]
                return v_u_950;
            end;
            v951.apply_to_emitter = function(p952, p953) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p953)
                f_apply_simple_size_anim(p953)
                f_apply_simple_transparency_anim(p953)
                p953.Rate = 20
                p953.Texture = p952:get_image()
            end;
            return v951;
        end)()))
        local v_u_954 = "Gambler (Kagetora)"
        local v_u_955 = "rbxassetid://87399577684695"
        local v_u_956 = "rbxassetid://74701000343356"
        v_u_17:add_fevericon_for_id(229, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_954, (copy 3): v_u_955, (copy 4): v_u_956, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v957 = v_u_5.FeverIconInfoBase:new()
            v957.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_954 ]]
                return v_u_954;
            end;
            v957.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_955 ]]
                return v_u_955;
            end;
            v957.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_956 ]]
                return v_u_956;
            end;
            v957.apply_to_emitter = function(p958, p959) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p959)
                f_apply_simple_size_anim(p959)
                f_apply_simple_transparency_anim(p959)
                p959.Rate = 20
                p959.Texture = p958:get_image()
            end;
            return v957;
        end)()))
        local v_u_960 = "Yapping"
        local v_u_961 = "rbxassetid://122903580460309"
        local v_u_962 = "rbxassetid://115990047455675"
        v_u_17:add_fevericon_for_id(230, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_960, (copy 3): v_u_961, (copy 4): v_u_962, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v963 = v_u_5.FeverIconInfoBase:new()
            v963.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_960 ]]
                return v_u_960;
            end;
            v963.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_961 ]]
                return v_u_961;
            end;
            v963.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_962 ]]
                return v_u_962;
            end;
            v963.apply_to_emitter = function(p964, p965) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p965)
                f_apply_simple_size_anim(p965)
                f_apply_simple_transparency_anim(p965)
                p965.Rate = 20
                p965.Texture = p964:get_image()
            end;
            return v963;
        end)()))
        local v_u_966 = "Wise Tree"
        local v_u_967 = "rbxassetid://138840569679124"
        local v_u_968 = "rbxassetid://99122531921256"
        v_u_17:add_fevericon_for_id(231, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_966, (copy 3): v_u_967, (copy 4): v_u_968, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v969 = v_u_5.FeverIconInfoBase:new()
            v969.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_966 ]]
                return v_u_966;
            end;
            v969.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_967 ]]
                return v_u_967;
            end;
            v969.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_968 ]]
                return v_u_968;
            end;
            v969.apply_to_emitter = function(p970, p971) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p971)
                f_apply_simple_size_anim(p971)
                f_apply_simple_transparency_anim(p971)
                p971.Rate = 20
                p971.Texture = p970:get_image()
            end;
            return v969;
        end)()))
        local v_u_972 = "Trumpet Skeleton"
        local v_u_973 = "rbxassetid://113536300062612"
        local v_u_974 = "rbxassetid://99074303431173"
        v_u_17:add_fevericon_for_id(232, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_972, (copy 3): v_u_973, (copy 4): v_u_974, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v975 = v_u_5.FeverIconInfoBase:new()
            v975.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_972 ]]
                return v_u_972;
            end;
            v975.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_973 ]]
                return v_u_973;
            end;
            v975.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_974 ]]
                return v_u_974;
            end;
            v975.apply_to_emitter = function(p976, p977) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p977)
                f_apply_simple_size_anim(p977)
                f_apply_simple_transparency_anim(p977)
                p977.Rate = 20
                p977.Texture = p976:get_image()
            end;
            return v975;
        end)()))
        local v_u_978 = "Scared Hamster"
        local v_u_979 = "rbxassetid://81252097653321"
        local v_u_980 = "rbxassetid://95102091557046"
        v_u_17:add_fevericon_for_id(233, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_978, (copy 3): v_u_979, (copy 4): v_u_980, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v981 = v_u_5.FeverIconInfoBase:new()
            v981.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_978 ]]
                return v_u_978;
            end;
            v981.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_979 ]]
                return v_u_979;
            end;
            v981.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_980 ]]
                return v_u_980;
            end;
            v981.apply_to_emitter = function(p982, p983) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p983)
                f_apply_simple_size_anim(p983)
                f_apply_simple_transparency_anim(p983)
                p983.Rate = 20
                p983.Texture = p982:get_image()
            end;
            return v981;
        end)()))
        local v_u_984 = "Popcat"
        local v_u_985 = "rbxassetid://135036452127137"
        local v_u_986 = "rbxassetid://83829549367113"
        v_u_17:add_fevericon_for_id(234, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_984, (copy 3): v_u_985, (copy 4): v_u_986, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v987 = v_u_5.FeverIconInfoBase:new()
            v987.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_984 ]]
                return v_u_984;
            end;
            v987.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_985 ]]
                return v_u_985;
            end;
            v987.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_986 ]]
                return v_u_986;
            end;
            v987.apply_to_emitter = function(p988, p989) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p989)
                f_apply_simple_size_anim(p989)
                f_apply_simple_transparency_anim(p989)
                p989.Rate = 20
                p989.Texture = p988:get_image()
            end;
            return v987;
        end)()))
        local v_u_990 = "Poor"
        local v_u_991 = "rbxassetid://133717695753850"
        local v_u_992 = "rbxassetid://121820184366085"
        v_u_17:add_fevericon_for_id(235, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_990, (copy 3): v_u_991, (copy 4): v_u_992, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v993 = v_u_5.FeverIconInfoBase:new()
            v993.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_990 ]]
                return v_u_990;
            end;
            v993.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_991 ]]
                return v_u_991;
            end;
            v993.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_992 ]]
                return v_u_992;
            end;
            v993.apply_to_emitter = function(p994, p995) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p995)
                f_apply_simple_size_anim(p995)
                f_apply_simple_transparency_anim(p995)
                p995.Rate = 20
                p995.Texture = p994:get_image()
            end;
            return v993;
        end)()))
        local v_u_996 = "Nyancat"
        local v_u_997 = "rbxassetid://98926605194257"
        local v_u_998 = "rbxassetid://86246048668472"
        v_u_17:add_fevericon_for_id(236, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_996, (copy 3): v_u_997, (copy 4): v_u_998, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v999 = v_u_5.FeverIconInfoBase:new()
            v999.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_996 ]]
                return v_u_996;
            end;
            v999.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_997 ]]
                return v_u_997;
            end;
            v999.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_998 ]]
                return v_u_998;
            end;
            v999.apply_to_emitter = function(p1000, p1001) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1001)
                f_apply_simple_size_anim(p1001)
                f_apply_simple_transparency_anim(p1001)
                p1001.Rate = 20
                p1001.Texture = p1000:get_image()
            end;
            return v999;
        end)()))
        local v_u_1002 = "I\'m Okay"
        local v_u_1003 = "rbxassetid://116754893248258"
        local v_u_1004 = "rbxassetid://97790936072367"
        v_u_17:add_fevericon_for_id(237, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1002, (copy 3): v_u_1003, (copy 4): v_u_1004, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1005 = v_u_5.FeverIconInfoBase:new()
            v1005.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1002 ]]
                return v_u_1002;
            end;
            v1005.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1003 ]]
                return v_u_1003;
            end;
            v1005.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1004 ]]
                return v_u_1004;
            end;
            v1005.apply_to_emitter = function(p1006, p1007) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1007)
                f_apply_simple_size_anim(p1007)
                f_apply_simple_transparency_anim(p1007)
                p1007.Rate = 20
                p1007.Texture = p1006:get_image()
            end;
            return v1005;
        end)()))
        local v_u_1008 = "Ceiling Cat"
        local v_u_1009 = "rbxassetid://108508531662226"
        local v_u_1010 = "rbxassetid://134991374255923"
        v_u_17:add_fevericon_for_id(238, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1008, (copy 3): v_u_1009, (copy 4): v_u_1010, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1011 = v_u_5.FeverIconInfoBase:new()
            v1011.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1008 ]]
                return v_u_1008;
            end;
            v1011.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1009 ]]
                return v_u_1009;
            end;
            v1011.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1010 ]]
                return v_u_1010;
            end;
            v1011.apply_to_emitter = function(p1012, p1013) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1013)
                f_apply_simple_size_anim(p1013)
                f_apply_simple_transparency_anim(p1013)
                p1013.Rate = 20
                p1013.Texture = p1012:get_image()
            end;
            return v1011;
        end)()))
        local v_u_1014 = "Butterfly"
        local v_u_1015 = "rbxassetid://138595292590219"
        local v_u_1016 = "rbxassetid://94232964684786"
        v_u_17:add_fevericon_for_id(239, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1014, (copy 3): v_u_1015, (copy 4): v_u_1016, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1017 = v_u_5.FeverIconInfoBase:new()
            v1017.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1014 ]]
                return v_u_1014;
            end;
            v1017.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1015 ]]
                return v_u_1015;
            end;
            v1017.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1016 ]]
                return v_u_1016;
            end;
            v1017.apply_to_emitter = function(p1018, p1019) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1019)
                f_apply_simple_size_anim(p1019)
                f_apply_simple_transparency_anim(p1019)
                p1019.Rate = 20
                p1019.Texture = p1018:get_image()
            end;
            return v1017;
        end)()))
        local v_u_1020 = "USAO (Chibi)"
        local v_u_1021 = "rbxassetid://70975408239190"
        local v_u_1022 = "rbxassetid://90754886787450"
        v_u_17:add_fevericon_for_id(240, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1020, (copy 3): v_u_1021, (copy 4): v_u_1022, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1023 = v_u_5.FeverIconInfoBase:new()
            v1023.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1020 ]]
                return v_u_1020;
            end;
            v1023.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1021 ]]
                return v_u_1021;
            end;
            v1023.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1022 ]]
                return v_u_1022;
            end;
            v1023.apply_to_emitter = function(p1024, p1025) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1025)
                f_apply_simple_size_anim(p1025)
                f_apply_simple_transparency_anim(p1025)
                p1025.Rate = 20
                p1025.Texture = p1024:get_image()
            end;
            return v1023;
        end)()))
        local v_u_1026 = "Summer Zara (OwEnigma)"
        local v_u_1027 = "rbxassetid://87447764434332"
        local v_u_1028 = "rbxassetid://107863916544698"
        v_u_17:add_fevericon_for_id(241, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1026, (copy 3): v_u_1027, (copy 4): v_u_1028, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1029 = v_u_5.FeverIconInfoBase:new()
            v1029.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1026 ]]
                return v_u_1026;
            end;
            v1029.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1027 ]]
                return v_u_1027;
            end;
            v1029.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1028 ]]
                return v_u_1028;
            end;
            v1029.apply_to_emitter = function(p1030, p1031) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1031)
                f_apply_simple_size_anim(p1031)
                f_apply_simple_transparency_anim(p1031)
                p1031.Rate = 20
                p1031.Texture = p1030:get_image()
            end;
            return v1029;
        end)()))
        local v_u_1032 = "Electroman V3"
        local v_u_1033 = "rbxassetid://104010028432781"
        local v_u_1034 = "rbxassetid://89704359413042"
        v_u_17:add_fevericon_for_id(242, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1032, (copy 3): v_u_1033, (copy 4): v_u_1034, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1035 = v_u_5.FeverIconInfoBase:new()
            v1035.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1032 ]]
                return v_u_1032;
            end;
            v1035.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1033 ]]
                return v_u_1033;
            end;
            v1035.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1034 ]]
                return v_u_1034;
            end;
            v1035.apply_to_emitter = function(p1036, p1037) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1037)
                f_apply_simple_size_anim(p1037)
                f_apply_simple_transparency_anim(p1037)
                p1037.Rate = 20
                p1037.Texture = p1036:get_image()
            end;
            return v1035;
        end)()))
        local v_u_1038 = "Summer Carnival (OwEnigma)"
        local v_u_1039 = "rbxassetid://101086435420957"
        local v_u_1040 = "rbxassetid://87178685245682"
        v_u_17:add_fevericon_for_id(243, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1038, (copy 3): v_u_1039, (copy 4): v_u_1040, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1041 = v_u_5.FeverIconInfoBase:new()
            v1041.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1038 ]]
                return v_u_1038;
            end;
            v1041.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1039 ]]
                return v_u_1039;
            end;
            v1041.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1040 ]]
                return v_u_1040;
            end;
            v1041.apply_to_emitter = function(p1042, p1043) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1043)
                f_apply_simple_size_anim(p1043)
                f_apply_simple_transparency_anim(p1043)
                p1043.Rate = 20
                p1043.Texture = p1042:get_image()
            end;
            return v1041;
        end)()))
        local v_u_1044 = "BlackY"
        local v_u_1045 = "rbxassetid://138589797371053"
        local v_u_1046 = "rbxassetid://135389402989179"
        v_u_17:add_fevericon_for_id(244, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1044, (copy 3): v_u_1045, (copy 4): v_u_1046, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1047 = v_u_5.FeverIconInfoBase:new()
            v1047.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1044 ]]
                return v_u_1044;
            end;
            v1047.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1045 ]]
                return v_u_1045;
            end;
            v1047.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1046 ]]
                return v_u_1046;
            end;
            v1047.apply_to_emitter = function(p1048, p1049) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1049)
                f_apply_simple_size_anim(p1049)
                f_apply_simple_transparency_anim(p1049)
                p1049.Rate = 20
                p1049.Texture = p1048:get_image()
            end;
            return v1047;
        end)()))
        local v_u_1050 = "Creo3D"
        local v_u_1051 = "rbxassetid://133036995546953"
        local v_u_1052 = "rbxassetid://107390545766137"
        v_u_17:add_fevericon_for_id(245, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1050, (copy 3): v_u_1051, (copy 4): v_u_1052, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1053 = v_u_5.FeverIconInfoBase:new()
            v1053.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1050 ]]
                return v_u_1050;
            end;
            v1053.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1051 ]]
                return v_u_1051;
            end;
            v1053.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1052 ]]
                return v_u_1052;
            end;
            v1053.apply_to_emitter = function(p1054, p1055) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1055)
                f_apply_simple_size_anim(p1055)
                f_apply_simple_transparency_anim(p1055)
                p1055.Rate = 20
                p1055.Texture = p1054:get_image()
            end;
            return v1053;
        end)()))
        local v_u_1056 = "Challenge Letter (Ardolf)"
        local v_u_1057 = "rbxassetid://75339276306168"
        local v_u_1058 = "rbxassetid://122821836952996"
        v_u_17:add_fevericon_for_id(246, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1056, (copy 3): v_u_1057, (copy 4): v_u_1058, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1059 = v_u_5.FeverIconInfoBase:new()
            v1059.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1056 ]]
                return v_u_1056;
            end;
            v1059.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1057 ]]
                return v_u_1057;
            end;
            v1059.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1058 ]]
                return v_u_1058;
            end;
            v1059.apply_to_emitter = function(p1060, p1061) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1061)
                f_apply_simple_size_anim(p1061)
                f_apply_simple_transparency_anim(p1061)
                p1061.Rate = 20
                p1061.Texture = p1060:get_image()
            end;
            return v1059;
        end)()))
        local v_u_1062 = "Energy of the Star (YooH)"
        local v_u_1063 = "rbxassetid://72983491951605"
        local v_u_1064 = "rbxassetid://115421287296575"
        v_u_17:add_fevericon_for_id(247, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1062, (copy 3): v_u_1063, (copy 4): v_u_1064, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1065 = v_u_5.FeverIconInfoBase:new()
            v1065.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1062 ]]
                return v_u_1062;
            end;
            v1065.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1063 ]]
                return v_u_1063;
            end;
            v1065.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1064 ]]
                return v_u_1064;
            end;
            v1065.apply_to_emitter = function(p1066, p1067) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1067)
                f_apply_simple_size_anim(p1067)
                f_apply_simple_transparency_anim(p1067)
                p1067.Rate = 20
                p1067.Texture = p1066:get_image()
            end;
            return v1065;
        end)()))
        local v_u_1068 = "Kagi"
        local v_u_1069 = "rbxassetid://73991191516431"
        local v_u_1070 = "rbxassetid://138744048510598"
        v_u_17:add_fevericon_for_id(248, ((function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_1068, (copy 3): v_u_1069, (copy 4): v_u_1070, (ref 5): f_apply_default_emitter_properties, (ref 6): f_apply_simple_size_anim, (ref 7): f_apply_simple_transparency_anim ]]
            local v1071 = v_u_5.FeverIconInfoBase:new()
            v1071.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): v_u_1068 ]]
                return v_u_1068;
            end;
            v1071.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1069 ]]
                return v_u_1069;
            end;
            v1071.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): v_u_1070 ]]
                return v_u_1070;
            end;
            v1071.apply_to_emitter = function(p1072, p1073) --[[ Name: apply_to_emitter ]] --[[ Line: 101 ]]
                --[[ Upvalues: (ref 1): f_apply_default_emitter_properties, (ref 2): f_apply_simple_size_anim, (ref 3): f_apply_simple_transparency_anim ]]
                f_apply_default_emitter_properties(p1073)
                f_apply_simple_size_anim(p1073)
                f_apply_simple_transparency_anim(p1073)
                p1073.Rate = 20
                p1073.Texture = p1072:get_image()
            end;
            return v1071;
        end)()))
        v_u_19:push_back(0)
        v_u_19:push_back(1)
        v_u_20:add_set_from_table_list(v_u_19._table)
    end;
    v_u_17.count = function(_) --[[ Name: count ]] --[[ Line: 2150 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        return v_u_18:count();
    end;
    v_u_17.add_fevericon_for_id = function(_, p1074, p1075) --[[ Name: add_fevericon_for_id ]] --[[ Line: 2154 ]]
        --[[ Upvalues: (copy 1): v_u_18, (ref 2): v_u_4 ]]
        if v_u_18:contains(p1074) then
            v_u_4:errf("add_fevericon_for_id already contains(%d)", p1074)
        end;
        p1075:set_id(p1074)
        v_u_18:add(p1074, p1075)
    end;
    v_u_17.get_fevericon_for_id = function(p1076, p1077) --[[ Name: get_fevericon_for_id ]] --[[ Line: 2162 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        local v1078 = v_u_18:get(p1077)
        if v1078 == nil then
            return p1076:get_default_fevericon();
        else
            return v1078;
        end;
    end;
    v_u_17.contains_fevericon_for_id = function(_, p1079) --[[ Name: contains_fevericon_for_id ]] --[[ Line: 2173 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        return v_u_18:contains(p1079);
    end;
    v_u_17.get_fevericon_default_available_ids_list = function(_) --[[ Name: get_fevericon_default_available_ids_list ]] --[[ Line: 2175 ]]
        --[[ Upvalues: (copy 1): v_u_19 ]]
        return v_u_19;
    end;
    v_u_17.get_fevericon_default_available_ids_set = function(_) --[[ Name: get_fevericon_default_available_ids_set ]] --[[ Line: 2176 ]]
        --[[ Upvalues: (copy 1): v_u_20 ]]
        return v_u_20;
    end;
    v_u_17.key_itr = function(_) --[[ Name: key_itr ]] --[[ Line: 2178 ]]
        --[[ Upvalues: (copy 1): v_u_18 ]]
        return v_u_18:key_itr();
    end;
    f_cons()
    return v_u_17;
end;
local v_u_1080 = v_u_5:new()
v_u_5.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 2185 ]]
    --[[ Upvalues: (copy 1): v_u_1080 ]]
    return v_u_1080;
end;
return v_u_5;
